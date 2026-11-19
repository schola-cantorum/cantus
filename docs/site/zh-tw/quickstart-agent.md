# Quickstart：一塊一塊把 Agent 組起來

其他幾份 quickstart 都是用一個模型問出一個答案。這一頁分六步組出一個完整的 agent，每一步只加一塊：model handle、工具、loop、身分、防護、記憶。每個區塊在任何機器上都能離線執行，因為這一頁用的模型是你自己寫腳本的那種。最後再換上真正的模型。

貫穿全頁的例子是一個學校福利社小幫手，負責從菜單報價。

## 需求

- Python 3.10 以上
- 已安裝 `cantus-agent`。這一頁不需要任何 extra，也不需要 API key。

```bash
uv pip install cantus-agent
```

## 1. Model handle

`Agent` 對模型只有一個要求：要有 `generate(prompt) -> str` 這個方法。任何有這個方法的物件都是 model handle。下面這個 class 會照順序回放你事先寫好的回覆，並把它收到的每一個 prompt 留下來，方便你之後查看。

```python
import json


class ScriptedModel:
    """照你寫好的腳本回放回覆的 model handle。"""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return json.dumps(self.replies.pop(0))


def call(name, **args):
    """模型想呼叫某個 tool 時給的回覆。"""
    return {"thought": "use a tool", "action": {"tool_name": name, "args": args}}


def answer(text):
    """模型做完時給的回覆。"""
    return {"thought": "done", "action": {"final_answer": text}}
```

這兩種 JSON 形狀就是模型與 agent loop 之間的全部約定：要嘛用名稱加引數呼叫一個 tool，要嘛給出最終答案。真正的模型產生的也是同樣的 JSON；這裡由你親手寫，所以你能清楚看到 loop 是對什麼做出反應。

## 2. 工具

寫一個有型別標註、有 docstring 的 Python 函式，再在上面加 `@tool`。`@tool` 會把函式變成 tool，但不會把它加到任何地方：你要在下一步把 tool 交給 agent，agent 再把每個 tool 的名稱、說明與引數 schema 給模型看。

```python
from cantus import tool

MENU = {"noodles": 60, "tea": 25}


@tool
def menu_price(item: str) -> int:
    """查詢福利社某一樣品項的價格。

    Args:
        item: 品項名稱，小寫。
    """
    return MENU.get(item, 0)


@tool
def add(a: int, b: int) -> int:
    """把兩個整數相加。

    Args:
        a: 第一個整數。
        b: 第二個整數。
    """
    return a + b


print(menu_price("tea"))  # tool 仍然可以自己直接呼叫
```

## 3. Loop

把模型和 tool 交給 `Agent`，再呼叫 `run`。agent 會組出 prompt、問模型、執行模型點名的 tool、把結果餵回去，如此重複，直到模型給出最終答案。

```python
from cantus import Agent

model = ScriptedModel([
    call("menu_price", item="noodles"),
    call("menu_price", item="tea"),
    call("add", a=60, b=25),
    answer("Noodles and tea cost 85 dollars."),
])
agent = Agent(model=model, tools=[menu_price, add])
state = agent.run("How much are noodles and tea together?")

for event in state.stream:
    print(type(event).__name__)
print(state.stream[-1].answer)
```

`state.stream` 就是 `EventStream`：模型做的每一個決定（`Action`）和每一個回來的結果（`Observation`），依序排列。三次 tool 呼叫加一個最終答案，一共七個事件。

## 4. 身分

`Soul` 描述這個 agent 是誰。它有六個段落，通常放在一個 `SOUL.md` 檔裡，用 `Soul.from_file(path)` 載入；`Soul.from_text` 則直接吃同樣格式的文字。把它傳給 `Agent(soul=...)`，它就會放在每一個 prompt 的最前面。

```python
from cantus import Soul

soul = Soul.from_text("""\
## Name & Role
Canteen helper for a senior high school.

## Personality
Brief and friendly.

## Rules
- Quote prices from the menu_price tool only.

## Tools
- menu_price(item)
- add(a, b)

## Output format
One short sentence.

## Handoffs
Send refund questions to the canteen office.
""")

model = ScriptedModel([answer("Hello! Ask me about the menu.")])
agent = Agent(model=model, tools=[menu_price, add], soul=soul)
agent.run("Who are you?")
print(model.prompts[0].splitlines()[0])  # prompt 現在以 soul 開頭
```

## 5. 防護

validator 是一個 hook，會在模型看到 tool 的結果之前先檢查它。檢查不過時，agent 記下的是一個帶著你那段 feedback 的 `ValidationErrorObservation`，而不是原本的結果；模型會再得到一輪機會自己修正。

```python
from cantus.hooks import Result, validator


@validator
def known_item(price: int) -> Result:
    """價格為零就拒絕：這個品項不在菜單上。"""
    if price > 0:
        return Result.success(price)
    return Result.failure("That item is not on the menu. Ask for noodles or tea.")


@tool(post_hook=known_item)
def menu_price(item: str) -> int:
    """查詢福利社某一樣品項的價格。

    Args:
        item: 品項名稱，小寫。
    """
    return MENU.get(item, 0)


model = ScriptedModel([
    call("menu_price", item="pizza"),
    call("menu_price", item="tea"),
    answer("Pizza is not on the menu; tea is 25 dollars."),
])
state = Agent(model=model, tools=[menu_price, add]).run("How much is pizza?")
print([type(event).__name__ for event in state.stream][1])
print(state.stream[1].feedback)
```

第二個 `def menu_price` 會把你腳本裡的 `menu_price` 這個名稱重新綁定到有防護的 tool，所以這個 agent 和之後建立的每個 agent 用的都是有防護的那一個。在它之前建立的 agent 仍然用沒有防護的那個；要套用防護，就重新建立那個 agent。

## 6. 記憶

`Agent.run` 每次都從零開始：agent 不會在兩次呼叫之間保留對話。記憶是另一個獨立的物件，由你自己的程式碼在每次 run 的前後讀寫。`ShortTermMemory(n=5)` 會保留最近五輪。

```python
from cantus import ShortTermMemory
from cantus.protocols.memory import Turn

memory = ShortTermMemory(n=5)


def chat(agent, text):
    """一輪對話：回想、執行、記住。"""
    past = "\n".join(
        f"User: {turn.user}\nAgent: {turn.assistant}" for turn in memory.recall(text)
    )
    state = agent.run(f"{past}\nUser: {text}" if past else text)
    reply = getattr(state.stream[-1], "answer", "")
    memory.remember(Turn(user=text, assistant=reply))
    return reply


model = ScriptedModel([
    answer("Nice to meet you, Mei."),
    answer("Your name is Mei."),
])
agent = Agent(model=model, tools=[menu_price, add], soul=soul)
chat(agent, "My name is Mei.")
print(chat(agent, "What is my name?"))
print("My name is Mei." in model.prompts[-1])  # 第二個 prompt 帶著第一輪的內容
```

六步跑完，你應該看到：

```text
25
CallToolAction
ToolObservation
CallToolAction
ToolObservation
CallToolAction
ToolObservation
FinalAnswerAction
Noodles and tea cost 85 dollars.
## Name & Role
ValidationErrorObservation
That item is not on the menu. Ask for noodles or tea.
Your name is Mei.
True
```

## 換上真正的模型

換成真正的模型後，上面的一切都不變。只有 model handle 換掉：

```python
from cantus import ChatModelAsHandle, load_chat_model

model = ChatModelAsHandle(load_chat_model("openai/gpt-4o-mini"))  # under docs tests: cantus_docs_model()
agent = Agent(model=model, tools=[menu_price, add], soul=soul)
print(chat(agent, "How much is tea?"))
```

`load_chat_model` 需要該 provider 的 extra 和一把 API key；[Quickstart（模型 API）](./quickstart-providers.md)列出八個 provider 各自的安裝指令、key 與 model spec，包含不需要 key 的本機後端。在 Colab 上，[Colab 版 Quickstart](./quickstart.md) 的 `mount_drive_and_load()` 回傳的就是可以直接交給 `Agent` 的 model handle。

真正的模型會自己寫回覆，所以它會做出腳本從來不會做的事：點錯 tool、傳錯引數，或是什麼都沒回答。loop 會把這些情況各自變成一個 observation，讓模型在下一輪讀到。想知道一次 run 裡發生了什麼，就把它重播出來：

```python
from cantus import Inspector

Inspector(state.stream).summary()  # action 與 observation 的數量
Inspector(state.stream).replay()   # 每個事件一行
```

## 接下來

- [Agent loop](./core/agent.md) — loop 的額度（`max_iterations`、`max_retries`）與三條錯誤路徑。
- [Tool](./protocols/tool.md)、[Validator](./protocols/validator.md)、[Memory](./protocols/memory.md)、[Identity (Soul)](./protocols/identity.md) — 這一頁每一塊的完整說明。
- [Workflows](./protocols/workflows.md) — 不靠模型，直接串接、分流、平行執行 tool。
- [Serve (HTTP)](./protocols/serve.md) 與 [channel cookbook](./channels/line.md) — 把 tool 放到 HTTP server 後面，再把聊天平台的訊息接到你的 agent。
