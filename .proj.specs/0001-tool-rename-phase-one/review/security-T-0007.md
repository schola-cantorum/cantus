# Security review：T-0007（Legacy construction names warn, visibly）

## 範圍

- Checkout：`cantus`，分支 `tickets/T-0007/legacy-construction-warnings`。
- Base（`main`）與 merge-base：`ab582c4eb6…`（`ab582c4`）；HEAD：`362b8427f4a57f2157e6b89f711820f9c8cbe0c5`。審查對象是 committed 層（三個 commit：`aa912b7`、`d98231b`、`362b842`；25 個檔，+2091／−163）；staged、unstaged、untracked 層都是空的。
- 審查對象的 `committed.diff` SHA-256：`ddab416737ebe85531e76429efd229c210f580376413e3977dc511fb56648d45`。本報告之後的修正（stage 6 與下表採納的強化）沒有再審。
- 方法：專案 `security-review` skill。一個 `harness-reviewer` 列出所有候選（不套用門檻），每個候選各由一個獨立的 `harness-reviewer` 做誤報過濾；reviewer 只讀檔，所有結論都是讀程式碼推理，沒有執行驗證。
- 信任邊界：cantus 是學生程式與 `cantus serve` 匯入的函式庫；model 輸出不可信；`sys.warnoptions`／`PYTHONWARNINGS` 來自行程環境（操作者）；`cantus serve --registry-import mod:attr` 匯入命令列指定的模組；`cantus serve` 可能面向網路。
- 本次變更的攻擊面：走訪 stack 並在呼叫者的 globals 寫入 `__warningregistry__` 的 deprecation helper；import 時修改 `warnings.filters`；warn option 解析；module `__getattr__` 別名；registry kind 對應與 `spec_for_llm()` 回傳的 dict 子類別；W13 吞掉被升級的警告；以 subprocess 寫入並執行腳本的測試。

## Findings

誤報過濾後，達到報告門檻（HIGH／MEDIUM 且 confidence ≥ 0.8）的 finding：**0**。

## 候選與處置

| ID | 位置 | 類別 | 候選嚴重度／信心 | 過濾結果（判定的信心） | 處置 |
|---|---|---|---|---|---|
| T0007-SEC-01 | `cantus/_deprecation.py:142（_option_covers_cantus），呼叫點 cantus/_deprecation.py:121、cantus/__init__.py:14` | denial_of_service / 輸入解析（warn option） | low／0.7 | 不成立（0.85） | 未確認為安全缺陷；正確性問題成立，已修：lineno 改用 `int()` 並接住 `ValueError`／`OverflowError`，與 Python 的解析一致。 |
| T0007-SEC-02 | `cantus/_deprecation.py:142` | filter_semantics（使用者的 warning filter 沒被尊重） | low／0.5 | 不成立（0.85） | 未確認為安全缺陷；語意落差成立，已修（同 SEC-01），列 44 加 `::+0` 案例。 |
| T0007-SEC-03 | `cantus/cli.py:183-186（_resolve_registry_import 只接 ImportError）；cantus/_deprecation.py:99-103；cantus/serve/app.py:245-256` | availability / 錯誤處理 | low／0.45 | 不成立（0.9） | 未確認為缺陷。操作者自己設 error filter 時，`--registry-import` 的模組若用舊名稱會以 traceback 結束，而不是 CLI 的錯誤格式。不在本票處理；記在票的 Comments 給 T-0012（保持 `--registry-import` 案例）與 T-0019（遷移指南）。 |
| T0007-SEC-04 | `cantus/_deprecation.py:185-191（_is_internal）` | warning attribution / filter scoping | low／0.25 | 不成立（0.9） | 未確認為安全缺陷；歸屬判斷過寬成立，已修：改以 frame 的模組名稱辨認 import 機制。`cantus.` 底下的第三方模組被跳過是 spec §2.4 指定的規則。 |
| T0007-SEC-05 | `cantus/_deprecation.py:173-181（_insert_visible_entry），cantus/__init__.py:12-14` | global state mutation / thread-safety（Python 3.14 / free-threaded） | low／0.2 | 不成立（0.9） | 未確認為缺陷。已採納為強化：`warnings._lock` 存在時在鎖內插入。free-threaded build 與 context-aware warnings 沒有驗證，記在票裡。 |
| T0007-SEC-06 | `cantus/_deprecation.py:99-103` | security signal suppression（W13 吞掉例外） | low／0.15 | 不成立（0.93） | 未確認為缺陷。W13 不外拋是 AC-22 的規定，本票尚未接線；「被吞掉時是否留痕」記在 Comments 給 T-0010。 |
| T0007-SEC-07 | `cantus/_deprecation.py:194-200（_attributed_frame），cantus/core/registry.py:23-54` | resource consumption（stack walk） | low／0.1 | 不成立（0.95） | 未確認為缺陷；不處理。 |
| T0007-SEC-08 | `tests/legacy/test_warning_visibility.py:319-360（_free_port 與 CLI serve 測試），tests/legacy/support.py:128-149` | test hygiene / 本機暴露 | low／0.2 | 不成立（0.9） | 未確認為缺陷。已採納為強化：CLI 測試明確傳 `--host 127.0.0.1`，子行程環境移除 `CANTUS_SERVE_*`。 |

### 各候選的說明

#### T0007-SEC-01

- **候選**：規則 1 解析 sys.warnoptions 時，只要 lineno 欄位 isdecimal() 為真就直接呼叫 int(lineno)，沒有包 try/except。Python 3.11 起 int() 對超過 4300 位數的十進位字串（int_max_str_digits 預設上限）會丟 ValueError。Python 自己的 warnings._setoption 會接住這個 ValueError，只印出「Invalid -W option ignored」後繼續執行（已對照本機 CPython 3.13 的 warnings.py:236-242）；cantus 版本則讓 ValueError 從 install_default_filter() 往外丟，而它是在 cantus/__init__.py 匯入時執行的，結果是 `import cantus` 整個失敗。違反的需求：stage 5 核准的讀法 C2-F1-a 寫明規則 1「依 Python 解析 -W 的方式」解析，且「Python 不接受的 entry 視為不存在」；Python 會忽略的選項，cantus 卻因此崩潰。
- **宣稱的影響**：可用性：所有 import cantus 的程式（含 `cantus serve`）都在匯入時崩潰，而同一個選項對 Python 本身無害。沒有程式碼執行，也沒有資料外洩。
- **攻擊者前提**：必須能控制行程的環境變數或命令列（依上游方法論屬受信任輸入），或是 CI/部署設定裡誤寫了很長的 lineno。Python 3.10 沒有位數上限，不會觸發。
- **建議的修正**：把 int(lineno) 包進 try/except (ValueError, OverflowError) 並在例外時 return False，與 Python 的 _setoption 對齊；或乾脆整個 _option_covers_cantus 呼叫都用 try/except 包起來，失敗時視為不涵蓋。
- **過濾者的理由**：結論：以 stage 7 安全審查來說是誤報。不過程式碼本身的正確性缺陷是真的，建議轉回 stage 6 code review 或開一張輕量票處理，不要列為安全 finding。以下全部是讀程式碼的推論，我沒有實際執行。

一、缺陷是否存在（推論，未執行）：存在，而且是這次變更新增的。committed.diff 第 357–390 行新增了 install_default_filter 和 _option_covers_cantus。cantus/_deprecation.py:142 寫的是 `if lineno and (not lineno.isdecimal() or int(lineno) != 0)`，int() 外面沒有 try/except。從 CPython 3.11 起，對超過 4300 位數的十進位字串呼叫 int() 會丟 ValueError；這個上限其實也已回補到 3.10.7 以後的版本，所以候選說「3.10 不會觸發」並不精確，只有 3.10.0 到 3.10.6 不會。這個 ValueError 會經過 cantus/_deprecation.py:121 的 any(...) 往外丟，再從 cantus/__init__.py:9 的 install_default_filter() 丟出（候選寫第 14 行，實際呼叫在第 9 行），結果就是 `import cantus` 失敗。CPython 自己的 warnings._setoption 會把 int(lineno) 的 (ValueError, OverflowError) 轉成 _OptionError，_processoptions 接住後只印「Invalid -W option ignored」。所以兩邊行為確實不同，也和 stage 5 核准的讀法「Python 不接受的 entry 視為不存在」不符。候選引用的本機 warnings.py:236-242 我沒能在 checkout 裡找到檔案確認，這部分是依我對 CPython 原始碼的記憶。

二、攻擊者能不能控制輸入：不能。唯一的來源是 sys.warnoptions，它只來自行程啟動時的 -W 參數或 PYTHONWARNINGS 環境變數。上游方法論的 false-positive 段落第 161 行寫明環境變數和 CLI flag 屬於受信任的值，依賴控制它們的攻擊一律無效。`cantus serve` 雖然可能面對網路，但 HTTP 請求寫不進 sys.warnoptions。檢查時機也只在匯入時，執行中不會再讀，所以網路攻擊者到不了這段程式碼。能設定這個值的人，本來就能直接改環境或不讓行程啟動，沒有跨越任何信任邊界。

三、影響類型：只有可用性。匯入失敗，沒有程式碼執行，沒有資料外洩，也沒有權限提升。上游方法論第 43、139 行把 DoS 和資源耗盡排除在回報範圍之外。在這個專案的信任模型下（學生在自己的機器或 Colab 上跑教學函式庫），這只是使用者對自己行程的誤設定。

四、建議：從安全 finding 移除。改用 P2 正確性缺陷轉給 stage 6，違反的需求是 C2-F1-a 規則 1「Python 不接受的 entry 視為不存在」。修法同候選建議：把 int(lineno) 包在 try/except (ValueError, OverflowError) 裡，失敗時 return False，並補一個超過 4300 位數 lineno 的測試。

#### T0007-SEC-02

- **候選**：cantus 的 lineno 判斷用 isdecimal()，Python 用的是 int() 加上 `>= 0` 檢查。Python 接受 `+0`、`-0`、`0_0` 這類 lineno，並當成 0（不限行號）處理；cantus 則視為有範圍或無效的 entry，於是不算數。例如 `-W ignore::DeprecationWarning::+0` 在 Python 眼中等同於對整個類別 ignore，cantus 規則 1 卻不認。一般情況下有規則 2 補救：選項建立的 entry 排在 __main__ default 之前，規則 2 不會插入。但在 IPython 那種把 `default::DeprecationWarning:__main__` 重新插到最前面的版面（測試 row 43/44 的情境），規則 2 會把 cantus 的 default entry 插在使用者的 ignore 前面，cantus 警告因此違反使用者意願而顯示出來。違反 C2-F1-a 的讀法：「lineno a non-negative integer… An entry counts when Python accepted it」。
- **宣稱的影響**：使用者明確要求隱藏的 DeprecationWarning（只限 cantus 類別）仍被印出。不會隱藏其他函式庫的警告，安全影響極低。
- **攻擊者前提**：無攻擊者情境，屬於設定語意不一致；需要特殊拼法的 lineno，外加 IPython/Jupyter 類型的 filter 版面。
- **建議的修正**：改成 `try: n = int(lineno) except (ValueError, OverflowError): return False`，再加上 `if n < 0: return False; if n != 0: return False`，完全照 Python 的 _setoption 邏輯。
- **過濾者的理由**：以安全缺陷來看，這是誤報；不過它描述的語意落差，用程式碼推論確實存在（我沒有執行驗證）。

(1) 語意落差成立。cantus/_deprecation.py:142 寫的是 `if lineno and (not lineno.isdecimal() or int(lineno) != 0): return False`。CPython 的 warnings._setoption（3.10 以後都一樣）是先 `int(lineno)`，再檢查 `< 0`，所以 `+0`、`-0`、`0_0` 都會被接受成 lineno=0，也就是不限行號。cantus 的 isdecimal() 卻把這三種拼法擋掉，_option_covers_cantus 因此回傳 False。

(2) 會顯示出來的路徑也成立。在一般 Python 版面裡，使用者的 `ignore::DeprecationWarning::+0` 排在 `default::DeprecationWarning:__main__` 前面，所以 _insert_visible_entry 碰到第一個符合的 entry 時 seen_main 還是 False，直接 return，不會插入。但在 IPython 版面裡，最前面先插了一筆 `default::DeprecationWarning:__main__` entry（ticket C2-F2、測試 row 43/44 模擬的就是這個）。這筆 entry 讓 seen_main=True，接著使用者的 ignore entry 符合第 173 行的條件，cantus 就把 `default` CantusDeprecationWarning 插到它前面。結果使用者明確要求隱藏的 cantus 棄用警告還是會印出來。這和 ticket 第 82–87 行「Readings approved at stage 5」裡 C2-F1-a 寫的「lineno a non-negative integer… An entry counts when Python accepted it」不一致。

(3) 安全上不成立的理由：
- 輸入來源是 sys.warnoptions（-W 或 PYTHONWARNINGS），由執行 Python 的使用者自己在自己的機器或 Colab 上設定，沒有跨越信任邊界。`cantus serve` 的網路請求也碰不到 interpreter 的 warnoptions。
- 後果只是多印出一則 CantusDeprecationWarning（stderr 上的固定文字，內容是棄用說明和 migration 連結），只限 cantus 自己的類別。它不會隱藏其他套件的警告，也不會洩漏資料、提升權限或執行程式碼。
- 觸發條件要同時有不常見的 lineno 拼法和 IPython/Jupyter 的 filter 版面，而且做這件事的人就是受影響的人本人。

這是新引入的程式碼（committed-cantus.diff 第 74–79 行顯示 cantus/_deprecation.py 是 new file），但它是正確性或規格符合度的問題，不是可被利用的安全缺陷。建議 parent 把它轉到 stage 6 code review，當作 C2-F1-a 符合度的低嚴重度（P2）項目處理。修法可以照候選說的改成 `try: n = int(lineno) except (ValueError, OverflowError): return False`，接著 `if n != 0: return False`（負數 Python 本來就拒絕，同樣回傳 False），並補一筆 `-W ignore::DeprecationWarning::+0` 搭配 IPython entry 的測試 row。

驗證方式：以上全部來自讀程式碼和我記得的 CPython 原始碼，沒有實際執行；我這次沒有讀 CPython 原始檔，所以 _setoption 的細節屬於記憶，不是讀檔得到的證據。

#### T0007-SEC-03

- **候選**：這張票讓 @skill、register_skill、get_registry()、kind "skill" 等舊名稱發出 CantusDeprecationWarning，W13 以外的 id 在 error filter 下一律往外 raise（_deprecation.py:102-103）。當操作者用 `-W error`、`PYTHONWARNINGS=error` 或 `error::DeprecationWarning` 執行（CI 與部分強化部署常見）時，有兩條路徑受影響：(a) `cantus serve --registry-import mod:attr` 匯入的模組只要用到舊名稱，importlib.import_module 就會丟出 CantusDeprecationWarning；它不是 ImportError，所以 _resolve_registry_import 接不到，CLI 直接噴出未處理的 traceback（含本機絕對路徑，只在本機 stderr），沒有走既有的「cannot import registry」錯誤訊息。(b) HTTP 呼叫的 tool 本體裡若使用舊名稱（例如在 run 內呼叫 get_registry() 或讀 spec["skill"]），每次請求都會變成 500。另有一項已查證的反面結果：session tracker 記錄的 ToolErrorObservation 訊息在 /introspection 會被遮蔽（introspection.py:359-362），所以警告文字不會經由 HTTP 外洩。在 error filter 下 raise 屬於 spec 刻意的行為；這裡回報的是 CLI 錯誤處理被繞過，以及這次可用性回歸。
- **宣稱的影響**：服務啟動失敗或請求失敗（可用性），錯誤訊息從乾淨的 CLI 錯誤退化成 traceback。沒有機密外洩。
- **攻擊者前提**：操作者自己設了 error filter，且載入的程式碼仍使用舊名稱，沒有外部攻擊者。
- **建議的修正**：在 _resolve_registry_import / _resolve_channels_import 加上 `except Warning as exc: raise RegistryImportError(...)`，或至少接 CantusDeprecationWarning，維持乾淨的錯誤輸出；在遷移指南（T-0019）註明 error filter 下舊名稱會讓 serve 啟動失敗。
- **過濾者的理由**：以安全審查的標準來看，這是誤報（false positive）。以下結論都是讀程式碼推得，沒有實際執行驗證。

1. 攻擊者控制不了輸入。要觸發這個問題，兩個條件都要由操作者自己設定：一是 error filter（`-W error`、`PYTHONWARNINGS`），二是用 `--registry-import` 指定的模組，或是會用到舊名稱的 tool 程式碼。依 upstream 方法論的 precedent 3，環境變數與 CLI 旗標屬於受信任的值。HTTP 請求的 body 只會成為 `skill_instance.run(**body)` 的參數，攻擊者沒辦法讓 tool 本體去呼叫 `get_registry()` 或讀 `spec["skill"]`；會不會呼叫舊名稱，取決於操作者寫的程式碼，不是請求內容。

2. 影響只限可用性，也就是啟動失敗或回 500。這正好落在 hard exclusion 1（DoS/服務中斷）。而且原 candidate 也承認，在 error filter 下 raise 是 spec 刻意設計的行為（`_deprecation.py:99-103`，只有 W13 例外）。

3. 沒有機密外洩。traceback 只會印到本機 stderr；`/introspection` 會遮蔽 `ToolErrorObservation`（這點原 candidate 已查過）。

4. 這不是這張票才引入的新漏洞類別。`cli.py:183-186` 原本就只接 `ImportError`。在 `-W error` 下，第三方套件匯入時發出的任何 `DeprecationWarning`，或模組內的其他例外，本來就會繞過 `RegistryImportError`，直接變成 traceback。HTTP 端點在 `app.py:245-256` 本來就會對 tool 的任何例外重新 raise，結果就是 500。

5. cantus 內部的 serve 路徑在這張票的範圍內不會自己觸發警告。我搜尋過 `cantus/` 下的 `get_registry()`、`["skill"]` 和 `.get("skill"`，除了定義本身以外沒有任何呼叫點；`introspection.py:322` 的 `DataflowNode kind="skill"` 不是 registry kind。`app.py:253-254` 雖然會建構 `CallSkillAction(skill_name=...)`，但在 HEAD 版本的 diff 中，W4 和 W7 沒有接到任何建構路徑（這張票只發出 W1、W2、W3、W8、W9）。所以在 error filter 下，一般請求不會因為 cantus 內部的程式碼而變成 500。

剩下的部分只是 CLI 錯誤體驗的問題：在 error filter 下，訊息從乾淨的 CLI 錯誤退化成 traceback。這可以當成 stage 6 的 P2 可讀性建議，或寫進遷移指南（T-0019）的說明，但不是安全缺陷。

#### T0007-SEC-04

- **候選**：_is_internal 只要 frame 的 __name__ 是 `cantus` 或以 `cantus.` 開頭，或檔名同時含有子字串 "importlib" 和 "_bootstrap"，就把它當成內部 frame 跳過。檔名判斷用的是子字串，不是精確比對 `<frozen importlib._bootstrap>` / `<frozen importlib._bootstrap_external>`，所以學生或第三方檔案路徑只要剛好含有這兩段字（例如 `~/importlib-practice/_bootstrap_hw.py`）就會被跳過。學生自建、名稱放在 `cantus.` 底下的外掛模組也會被跳過。結果是警告歸到下一個 frame，warn_explicit 的 module= 也跟著換掉，於是 `-W error::DeprecationWarning:mymod` 或 `filterwarnings(module=...)` 這類依模組設定的 filter 可能不觸發，或套到錯的模組上。
- **宣稱的影響**：警告歸屬錯誤，依模組設定的 error/ignore filter 失效（只影響 cantus 類別），沒有直接的安全影響。
- **攻擊者前提**：需要特定檔案路徑或模組命名，屬意外而非攻擊。
- **建議的修正**：檔名比對改成精確集合 {"<frozen importlib._bootstrap>", "<frozen importlib._bootstrap_external>"}，或判斷 f_globals['__name__'] in {'importlib._bootstrap', 'importlib._bootstrap_external'}；模組名稱的判斷也可以改用 cantus 套件目錄的實際路徑。
- **過濾者的理由**：已讀：manifest.md（base/merge-base ab582c4e、HEAD 362b8427，只有 committed 層）、committed.diff 中 _is_internal／_attributed_frame 的段落（diff 第 433-446 行，以及測試 test_attribution_skips_importlib_bootstrap_frames 在第 1857 行）、checkout 中的 cantus/_deprecation.py 全檔，還有 upstream-security-review.md 的 FALSE POSITIVE FILTERING 段落。以下全部是讀程式碼推論出來的，沒有實際執行。

程式碼的描述是對的：_deprecation.py:191 用 `"importlib" in filename and "_bootstrap" in filename` 做子字串比對，:188 則是只要 __name__ 是 cantus 或以 `cantus.` 開頭就跳過。所以路徑同時含有這兩段字的使用者檔案，或自己命名成 cantus.* 的模組，都會被當成內部 frame 跳過，警告就歸到外面一層的 frame。

但它不構成安全缺陷，理由如下：
(1) 攻擊者控制不了輸入。co_filename 和 f_globals['__name__'] 來自本機上被 import 或執行的程式碼的路徑和模組名，只有在本機或 Colab 執行程式的學生本人（或他自己裝的套件）能決定，不在信任邊界之外。`cantus serve` 收到的網路請求只能影響訊息內容，例如 W13 在解析模型輸出時觸發，但影響不到呼叫堆疊上各 frame 的檔名或模組名。
(2) 沒有能觀察到的安全影響。最壞的結果是 CantusDeprecationWarning 歸錯模組，於是依模組設定的 `-W`／filterwarnings 不觸發（警告照樣印出），或套到外層模組上（變成 raise 或被忽略）。這只是 deprecation 警告的顯示和診斷問題，不涉及授權、資料外洩或程式碼執行。另外 W13 這條會被網路觸發的路徑，在 :99-103 已經吞掉 CantusDeprecationWarning，就算 error filter 被誤套用，也不會從網路端引發例外。
(3) 依 upstream 準則，它屬於「沒有證明有安全影響的非安全關鍵欄位比對」和「缺少強化措施」（HARD EXCLUSIONS 5、7），而且沒有具體的攻擊路徑（SIGNAL QUALITY 1、2）。
(4) 依 cantus 的 `cantus.` 命名空間判斷內部 frame，是刻意的設計；學生把自己的模組取名為 cantus.* 本來就是在冒用套件命名空間，算不上新引入的漏洞。

結論：從安全角度看，這是 false positive。如果要追究，它頂多是程式碼品質問題（P2），例如把檔名比對收斂成精確集合 {"<frozen importlib._bootstrap>", "<frozen importlib._bootstrap_external>"}，或改用 f_globals['__name__'] 比對。這屬於 stage 6 code review 的範圍，不是 stage 7 的安全 finding。

#### T0007-SEC-05

- **候選**：匯入時直接 warnings.filters.insert(...)，接著呼叫 _filters_mutated 或 _filters_mutated_lock_held，整個過程都沒有取得 warnings 模組的鎖。Python 3.14 把 API 改名為 _filters_mutated_lock_held，名稱本身就表示呼叫端必須持有 warnings._lock；在 free-threaded（3.14t）或 context-aware warnings 模式下，這樣做可能與其他執行緒的 filter 修改發生競態，或修改到不是目前生效的 filter 清單。這是以 CPython 3.14 的 API 命名推論的，本機只有 3.13，無法驗證；票上記錄 3.10–3.14 測試通過，但沒提到 free-threaded build。另外，這次修改只新增 CantusDeprecationWarning 類別的 default entry，經檢查不會隱藏其他函式庫的警告。
- **宣稱的影響**：可能出現 filter 清單競態或插入失效（警告顯示與否不如預期），沒有程式碼執行或資料外洩。
- **攻擊者前提**：無攻擊者，需要多執行緒同時首次 import cantus 並修改 warnings，或執行在 free-threaded / context-aware 模式。
- **建議的修正**：有 warnings._lock 時改用 `with warnings._lock:` 包住插入與 mutated 呼叫；或改用公開 API（warnings.filterwarnings 搭配 append=False 後再調整位置）；在 3.14t 上加一個 subprocess 測試。
- **過濾者的理由**：以下是靜態程式碼推論，沒有實際執行，本機也沒有 3.14 或 3.14t 可以驗證。

1. 攻擊者無法控制輸入：`_insert_visible_entry` 只讀取行程內的 `warnings.filters`，插入的固定值是 `("default", None, CantusDeprecationWarning, None, 0)`。唯一的外部輸入是 `sys.warnoptions`，也就是執行者自己下的 `-W` 或 `PYTHONWARNINGS`，屬於本機操作者的信任範圍。`cantus serve` 收到的網路請求不會走到這段程式碼。

2. 觸發時機與次數有限：呼叫鏈是 `cantus/__init__.py:9` → `install_default_filter()`，只在第一次 import 時執行。之後由 `_filter_installed` 旗標（`_deprecation.py:117-120`）擋住重複執行，Python 的 per-module import lock 也確保多執行緒同時 import 時只會跑一次。要出現競態，必須在 import cantus 的同一瞬間，另有執行緒在修改 warnings filter，而且要在 free-threaded build 上。

3. 影響沒有安全意義：最壞的情況是某個 CantusDeprecationWarning 該顯示時沒顯示，或 filter 快取版本號沒有正確更新。不會執行程式碼、不會洩漏資料、不會跨過權限邊界，也不會壓掉其他函式庫的警告，因為這段只會在 Python 預設的 `ignore::DeprecationWarning` 前面多插一個範圍很窄的 default entry。

4. 依方法論應排除：`upstream-security-review.md:146` 的 hard exclusion 第 8 條寫明，只是理論上可能、不會實際造成問題的競態條件不要回報。`:39-40` 也要求確信可利用度超過 80%，並略過理論性與低影響的問題。

5. 3.14 的 context-aware warnings：如果 import 剛好發生在 `catch_warnings` 區塊內，插入的 entry 可能只寫進全域 filter 清單，不會出現在目前 context 的清單裡。結果只是警告可見度和預期不同，屬於功能或健壯性層面，不是新引入的安全缺陷。

可以轉給 stage 6 或健壯性追蹤的低優先改善（不算安全 finding）：有 `warnings._lock` 時改用 `with warnings._lock:` 包住插入和版本更新；另外考慮在 3.14t 上加一個子行程測試。這部分要確認的話，需要在 CPython 3.14 / 3.14t 實際執行，並查證 `_filters_mutated_lock_held` 在 release build 是否會檢查呼叫端有沒有持鎖。我推論 release build 只會遞增版本號，但沒有驗證過。

#### T0007-SEC-06

- **候選**：W13 在 filter 升級成 error 時被 except 吞掉，不 raise、不顯示，也不留下任何紀錄。操作者如果用 `-W error` 偵測模型輸出中的舊 action key（或異常輸出），會完全收不到訊號，連 stderr 都沒有。這是 spec AC-22 刻意的設計，而且 W13 在這張票還沒接到解析路徑（grep 只在 _TABLE 中出現），所以列為紀錄。另外，這個 except 也會吞掉自訂 showwarning 鉤子所丟出的 CantusDeprecationWarning（極端情況）。
- **宣稱的影響**：在 error 模式下失去可觀測性，不會造成越權或資料外洩。
- **攻擊者前提**：能影響模型輸出（prompt injection），且操作者依賴 error filter 偵測。
- **建議的修正**：W13 被吞掉時改用 warnings.showwarning 或 logging 至少印出一次，或在 EventStream 記一筆，讓 error 模式下仍有痕跡；由 T-0010 接線時決定。
- **過濾者的理由**：（程式碼推理，未實際執行）這個候選項不算本變更新增、可被利用的安全缺陷，理由有四點。

1. 攻擊者控制的輸入到不了這段程式碼。在被審查的 HEAD 上，產品程式碼裡沒有任何地方用 "W13" 呼叫 warn_legacy。grep 顯示 warn_legacy 的呼叫點只出現在 W1/W2/W3（cantus/protocols/skill.py、cantus/__init__.py）和 W8/W9（cantus/core/registry.py）。W13 只出現在 _TABLE 和 except 分支。模型輸出解析路徑要到 T-0010 才接上，所以在這張票裡，「模型輸出 → W13 → 被吞掉」這條資料流並不存在。
2. 被吞掉的東西不是安全控制。CantusDeprecationWarning 是 DeprecationWarning 的子類別，用來提醒使用者改用新名稱，不是偵測 prompt injection 或異常輸出的機制。沒收到它不會造成越權、資料外洩或繞過信任邊界，頂多少了一個遷移提示。說它是「安全訊號」，前提是操作者拿 deprecation filter 當入侵偵測用，這不是這個專案的信任模型，規格裡也沒有這種契約。
3. 這是規格明確要求的行為，而且當初就是為了堵住一個安全問題。traceability.md:175 規定「W13 is never raised as an exception」，AC-22 要求 filter 會把 W13 升級成例外時，Agent.run 和 parse_tool_call 仍要以相同結果完成。這項規定來自 round-1 的 R-1：不受信任的模型輸出加上 -W error，可能把 W13 變成例外並打斷 agent loop，也就是 prompt injection 能誘發的 DoS。這裡的 except 正是把那個問題擋掉。照候選項的建議改回拋出例外，就等於重新打開 R-1。
4. 「自訂 showwarning 鉤子丟出 CantusDeprecationWarning 也會被吞掉」這一點同樣只適用於 W13；第 102 行的條件會讓其他 W id 照常拋出。W13 目前沒有呼叫點，要觸發還得由使用者自己在本機安裝會丟例外的鉤子。這屬於使用者自己的環境，不是攻擊者能控制的東西。

另外，規格與票卡其實已經處理了「error 模式下看不到 W13」這件事。T-0016 改用「在 import cantus 之後於程式碼中設定 filter，並要求 stderr 不含 CantusDeprecationWarning」來檢查 W13（round-2 R2-1）。所以這是已知、有登記的設計取捨，不是遺漏。其中的可觀測性建議（例如被吞掉時至少用 logging 或 showwarning 留下一筆紀錄）可以交給 T-0010 接線時考慮，但不構成本票的安全 finding。

#### T0007-SEC-07

- **候選**：每次使用舊名稱都會從呼叫端往外走 frame 鏈，直到找到第一個非 cantus 的 frame，成本是 O(stack 深度)，再加上 warn_explicit 的 filter 比對。若學生在深層遞迴或熱迴圈中使用 `"skill" in spec`、`spec["skill"]`、`names_for("skill")`，每次都要付這筆成本。深度受 recursionlimit 限制，__warningregistry__ 的鍵為 (text, category, lineno)，也是有上限的，所以實際風險極低。
- **宣稱的影響**：效能，可忽略。
- **攻擊者前提**：無外部攻擊面，模型輸出無法觸發這些路徑（kind 一律是程式內常數）。
- **建議的修正**：不需修正；如有疑慮，可在 W9 等熱路徑以 registry 的 'version' 機制提早結束，或接受現狀。
- **過濾者的理由**：判定為誤報（false positive）。以下結論全部來自閱讀程式碼，沒有實際執行或量測。

一、成本有上限，而且是 Python 本身的常規做法。cantus/_deprecation.py:194-200 的 `_attributed_frame` 從 `sys._getframe(2)` 開始往外走，遇到第一個不屬於 cantus、也不屬於 importlib `_bootstrap` 的 frame 就停下（:198）。因為一開始就跳過 warn_legacy 與 `_attributed_frame` 自己，實際走過的 frame 只有 cantus 內部那幾層，再加上 import 機制的幾層，通常是常數級。只有整條呼叫鏈都屬於 cantus 時才會走到最外層，而那也受 recursionlimit 限制。`warnings.warn_explicit` 的 filter 比對與 `__warningregistry__` 查詢，跟一般 `warnings.warn(stacklevel=N)` 的成本屬於同一個量級，不是這次變更新增的放大器。

二、攻擊者控制不了輸入，碰不到觸發條件。W9 只在 `kind == "skill"`（registry.py:25），或 ToolSpecMapping 的鍵是 `"skill"`（:39、:45、:51）時觸發。我在 cantus/ 內查過所有呼叫點：`names_for`、`lookup`、`register` 傳入的 kind 一律是字串常數 `"tool"`，例如 serve/app.py:155、:165，serve/introspection.py:226-227、:320，serve/dashboard.py:88-89，core/agent.py:299、:351、:353，grammar/tool_call.py:51、:123。`spec_for_llm()` 的結果也沒有拿 HTTP 請求或模型輸出當鍵去索引。所以只有學生自己的程式碼寫了舊名稱，才會走到這條路徑。這是本機或 Colab 上的信任邊界內行為，`cantus serve` 的網路端也無法觸發。

三、沒有可觀察的安全影響。最壞情況只是學生自己的熱迴圈裡，每次呼叫多出幾層 frame 走訪，屬於效能上的細節，不會造成阻斷服務（DoS）、資訊洩漏或權限問題。依 upstream-security-review 的誤報過濾原則，這類「只有開發者自己能觸發、影響可忽略的資源消耗」應該排除。

剩下的不確定：上面的效能判斷沒有經過基準測試（benchmark）。如果使用者想追效能，可以另外當成 P2 等級的非安全改善項目處理，不應算作 stage 7 的安全 finding。

#### T0007-SEC-08

- **候選**：row 45 的 CLI 測試以子行程啟動真正的 `cantus serve`。它沿用整個開發者環境（只移除 PYTHONWARNINGS、PYTHONDEVMODE），沒有指定 --host，也沒有設定 auth。如果開發者 shell 中有 CANTUS_SERVE_HOST=0.0.0.0（Settings 的 env_prefix 是 CANTUS_SERVE_），測試期間（最長約 30 秒）會在所有網卡上開出一個免驗證的服務，包含 reg_tool 端點、dashboard 與 introspection。_free_port 先綁定再釋放埠號，有 TOCTOU 競態（測試不穩定，不是安全問題）。run_python 號稱「clean environment」，實際上只移除三個變數，其他環境變數（含 API key）都會傳給子行程。腳本內容是測試自己寫的固定字串，不會印出環境，所以沒有發現外洩路徑。
- **宣稱的影響**：短暫暴露測試用的免驗證服務（只有回傳輸入值的 tool），影響很小。
- **攻擊者前提**：開發者環境本身設了對外的 host，且攻擊者與開發機在同一網路並在測試的 30 秒內連線。
- **建議的修正**：CLI 測試明確傳入 `--host 127.0.0.1`，並在 env 中移除所有 CANTUS_SERVE_* 變數；run_python 的 docstring 改成實際行為，或改用白名單環境。
- **過濾者的理由**：讀過的輸入有 manifest.md（base/merge-base ab582c4、HEAD 362b842，只有 committed layer），以及 checkout 內的 tests/legacy/test_warning_visibility.py:319-386、tests/legacy/support.py:128-149、cantus/cli.py:54-64、cantus/config.py:57，還有 upstream-security-review.md 的排除規則。結論只來自程式碼推理，沒有實際執行。

候選描述的機制本身成立：CLI 測試（第 325-356 行）呼叫 `cantus serve` 時只帶 `--registry-import` 和 `--port`，沒有 `--host`，env 沿用 os.environ，只拿掉 PYTHONWARNINGS 和 PYTHONDEVMODE。cli.py:58 寫明 host 的預設值是「CANTUS_SERVE_HOST env or 127.0.0.1」，config.py:57 的 env_prefix 是 "CANTUS_SERVE_"。所以開發者環境如果設了 CANTUS_SERVE_HOST=0.0.0.0，子行程確實會綁定所有網卡。

但這不構成可利用的漏洞，理由有四：

1. 攻擊者控制不了觸發條件。對外 host 這個前提完全來自開發者自己的環境變數。upstream 規則 3 寫明，環境變數和 CLI flag 是受信任的值，依賴控制環境變數的攻擊不成立。
2. 這是只在測試時執行的程式碼，不會隨 cantus-agent 發佈，正是 upstream 排除規則 11 所列的「files that are only unit tests」。
3. 子行程也會繼承同一份環境裡的 CANTUS_SERVE_AUTH_MODE、BEARER_TOKEN 等設定。開發者如果刻意設定對外 host，所得到的暴露程度和他自己手動執行 `cantus serve` 一樣。測試沒有降低任何安全邊界，也沒有引入新的暴露面。服務只提供回傳輸入整數的 reg_tool，存活時間最多約 30 秒，結束後會 terminate/kill。
4. 其他兩點不是安全問題。_free_port 的 TOCTOU 只會讓測試不穩定，埠號被搶走時伺服器會啟動失敗，候選本身也承認這一點。run_python 的 docstring 說「clean environment」但只移除三個變數，這是文件和實際行為不一致。子行程執行的是測試寫死的腳本，不會印出環境，也沒有外洩路徑。

至於「新引入」：這個測試確實是本 ticket 新增的，但只新增了測試用的子行程，沒有新增 product 的安全表面。

可改為非安全項目交給 code review 處理：明確傳入 `--host 127.0.0.1`，可以讓測試不受開發者環境影響。run_python 的 docstring 改成符合實際行為，屬於 P2 等級的 test hygiene，不屬於 stage 7 的安全發現。

## 涵蓋範圍與限制

已讀的必要輸入：manifest.md、commits.txt（aa912b7、d98231b、362b842）、stat.txt、committed-cantus.diff（全部）、committed-tests.diff（全部 2054 行，分兩段讀完）、committed-ticket.diff（含 stage 5 核准的讀法）、.claude/skills/security-review/references/upstream-security-review.md、docs/agents/review.md（security 段）、docs/agents/runtime.md、.proj.specs/OPEN-QUESTIONS.md（確認 OQ-010 至 OQ-012 不在範圍內）。依任務要求的 methodology 讀了 upstream 檔；.claude/skills/security-review/SKILL.md 本身沒有另外讀，以 parent 指定的 methodology 為準。我沒有自己跑 live git diff，以 packet 為準；checkout 只用來讀周邊程式（HEAD 362b842，manifest 記載 clean，我沒有權限執行 git 再次驗證）。

讀過的周邊程式：cantus/_deprecation.py（HEAD 全檔 70-201 行）、cantus/core/registry.py（全檔）、cantus/__init__.py（__getattr__）、cantus/protocols/tool.py（_to_tool、register_tool）、cantus/core/agent.py:170-369（_build_prompt 與不受信任模型輸出的解析和派送）、cantus/serve/app.py:140-279（端點例外處理、session tracker）、cantus/serve/introspection.py（ToolErrorObservation 訊息遮蔽，359-362）、cantus/cli.py:165-294（--registry-import 解析）、cantus/config.py（Settings 預設 host=127.0.0.1、auth_mode=none、env_prefix）、本機 CPython 3.13.11 的 warnings.py（_setoption、_getaction、_getcategory、warn_explicit、_filters_mutated），用來比對 parser 語意。

查過而沒有發現缺陷的項目：(1) 模型輸出無法影響 registry kind，各呼叫點都是常數 \"tool\"，W13 在這張票還沒接線；(2) ToolSpecMapping 經 json.dumps 只輸出 \"tool\"，registry 層級的 spec_for_llm 沒有進入任何 HTTP 回應（dashboard/introspection 用的是個別 instance 的 spec_for_llm）；(3) pickle/copy 沒有新增反序列化 sink，ToolSpecMapping 沒有覆寫 __setitem__ 或 __reduce__；(4) 插入的 filter 只有 CantusDeprecationWarning 的 default entry，不會隱藏其他函式庫的警告，也不會蓋過使用者先設的 error/ignore；(5) _option_covers_cantus 不會 import 選項中指名的模組（Python 自己的 _getcategory 會，這屬於 Python 既有行為）；(6) 警告中的本機絕對路徑只出現在 stderr/log，與標準 warnings 行為相同；introspection 會遮蔽例外訊息，沒有經由 HTTP 外洩；(7) __warningregistry__ 的 setdefault 與 stdlib warnings.warn 行為一致；(8) 測試的子行程以 list argv 搭配 sys.executable 執行，沒有 shell，腳本是固定字串，沒有執行不受信任的輸入。

沒有做的項目：依賴/供應鏈掃描（這次沒有依賴變更，沒有執行 pip-audit）、實際執行測試或 PoC（沒有 Bash，SEC-01 的 int_max_str_digits 行為依 CPython 文件與原始碼推論）、Python 3.14 / free-threaded build 的實測（本機只有 3.13，SEC-05 屬於推論）、TUI 與 adapters 目錄（這次 diff 沒有動到）、channel gateway、跨票串鏈分析（屬於 epic close-out）。依指示 OQ-010 至 OQ-012，以及票中 Comments 列給 T-0008 至 T-0020 的名稱與文字，都沒有列為缺陷。

未涵蓋：相依套件掃描（本票沒有改相依）；其他作業系統；Python 3.14 free-threaded build；真實的 IPython kernel（stage 8 另行驗證行為，不是安全審查）。跨票的 chain analysis 在 epic close-out 進行。
