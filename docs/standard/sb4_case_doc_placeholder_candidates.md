# SB4 案件CS プレースホルダ候補メモ

## 目的

`CASE_DOC_MASTER_SOURCE=export_file` でAccessDB抽出Excelファイルを読み込み、案件CS生成まで確認した結果をもとに、MVPで仮利用するプレースホルダと今後追加候補を整理する。

## MVPでの前提

- MVPでは `C:\Users\clove\Downloads\UNISBC` 配下のExcelファイル群を、AccessDBから抽出したテーブルの仮入力として扱う。
- プレースホルダは本番確定ではなく、MVP検証用の仮定義とする。
- `TTS_HOST` / `TTS_IP` / `TTS_PORT` も仮定義とし、正式な取得元・命名は実データ確認後に確定する。
- 2026-05-12時点で確認した抽出Excelは `FS.xlsx` / `GUI.xlsx` / `HFS.xlsx` / `HSS.xlsx` / `MSW.xlsx` / `RAID.xlsx` / `SBC.xlsx` / `SCCE.xlsx` / `ユニット構成.xlsx`。

## UNISBC抽出列一覧

2026-05-13時点で `C:\Users\clove\Downloads\UNISBC` 配下から抽出した列名。MVPの仮プレースホルダは、この列名を根拠に段階的に追加する。

| Excel | ヘッダー行 | 列数 | 列名 |
| --- | ---: | ---: | --- |
| `FS.xlsx` | 1 | 13 | `ホスト名`<br>`eth2`<br>`eth0`<br>`eth3`<br>`eth1`<br>`保守LANフローティングIPアドレス`<br>`リモートシェルコマンド用フローティングIPアドレス`<br>`コマンド用フローティングIPアドレス`<br>`装置監視A用フローティングIPアドレス`<br>`装置監視B用フローティングIPアドレス`<br>`外部EMS一般コマンド用フローティングIPアドレス`<br>`外部EMSアラーム用フローティングIPアドレス`<br>`保守LANフローティングIPアドレス（SBY用）` |
| `GUI.xlsx` | 1 | 13 | `ホスト名`<br>`EMSコマンド用IPアドレス`<br>`EMSアラーム用IPアドレス`<br>`APL付与のフローティングIPアドレス`<br>`APL付与のフローティングIPアドレスのサブネットマスク`<br>`iLO用`<br>`収容形態`<br>`BCR02のIPアドレス(ループバックIPアドレス)`<br>`TTS-Host`<br>`TTS-IP`<br>`TTS-Port`<br>`AGENT_NO`<br>`WEB_DEVICE_NO` |
| `HFS.xlsx` | 1 | 10 | `ホスト名`<br>`装置監視用 IPアドレス`<br>`コマンド投入用 IPアドレス`<br>`NTP向け IPアドレス`<br>`アラーム送信用 IPアドレス`<br>`ホスト-ゲスト用 IPアドレス`<br>`iLO用 IPアドレス`<br>`TTS-Host`<br>`TTS-IP`<br>`TTS-Port` |
| `HSS.xlsx` | 1 | 11 | `ホスト名`<br>`装置監視用 IPアドレス`<br>`コマンド投入用 IPアドレス`<br>`NTP向け IPアドレス`<br>`アラーム送信用 IPアドレス`<br>`ホスト-ゲスト用 IPアドレス`<br>`iLO用 IPアドレス`<br>`iLO用DGW`<br>`TTS-Host`<br>`TTS-IP`<br>`TTS-Port` |
| `MSW.xlsx` | 1 | 5 | `ホスト名`<br>`保守・装置監視用`<br>`TTS-Host`<br>`TTS-IP`<br>`TTS-Port` |
| `RAID.xlsx` | 1 | 6 | `ホスト名`<br>`保守・装置監視用`<br>`MSW収容ポート番号`<br>`TTS-Host`<br>`TTS-IP`<br>`TTS-Port` |
| `SBC.xlsx` | 1 | 31 | `ホスト名`<br>`eth0`<br>`eth1`<br>`eth2`<br>`eth3`<br>`呼処理用フローティングIPアドレス`<br>`呼処理用フローティングIPアドレス（ｖ６）`<br>`SIGTRAN1IPアドレス`<br>`SIGTRAN2IPアドレス`<br>`コマンド用フローティングIPアドレス`<br>`保守アラーム用LANフローティングIPアドレス`<br>`リモートシェルコマンド用フローティングIPアドレス`<br>`NTP向けフローティングIPアドレス`<br>`住所情報装置向けフローティングIPアドレス`<br>`運用データ転送用フローティングIPアドレス`<br>`CL_ID`<br>`CA_ID`<br>`ソフト種別`<br>`冗長ルート切替試験用ポート(ens1f0用)`<br>`冗長ルート切替試験用ポート(ens4f0用)`<br>`冗長ルート切替試験用ポート(ens1f1用)`<br>`冗長ルート切替試験用ポート(ens4f1用)`<br>`冗長ルート切替試験用ポート(eno5用)`<br>`冗長ルート切替試験用ポート(ens2f0用)`<br>`ノードID`<br>`SIP-ID`<br>`AR-ID`<br>`住所情報サーバID`<br>`ISCエリアID`<br>`収容府県`<br>`直収端末番号` |
| `SCCE.xlsx` | 1 | 17 | `ホスト名`<br>`保守・装置監視用`<br>`TTS-Host`<br>`TTS-IP`<br>`TTS-Port`<br>`VLAN「TGEX/0/4」`<br>`VLAN「TGEX/0/6」`<br>`VLAN「TGEX/0/11」`<br>`VLAN「TGEX/0/13」`<br>`VLAN「TGEX/0/18」`<br>`VLAN「TGEX/0/20」`<br>`untagVLAN「TGEX/0/4」`<br>`untagVLAN「TGEX/0/6」`<br>`untagVLAN「TGEX/0/11」`<br>`untagVLAN「TGEX/0/13」`<br>`untagVLAN「TGEX/0/18」`<br>`untagVLAN「TGEX/0/20」` |
| `ユニット構成.xlsx` | 1 | 60 | `FSクラスタ名`<br>`ブロック`<br>`装置設置府県`<br>`装置設置ビル`<br>`F更BU_ビル名`<br>`F更BU_ビルコード`<br>`GUI_0系`<br>`GUI_1系`<br>`MSW_0系`<br>`MSW_1系`<br>`RAID_0系`<br>`RAID_1系`<br>`FS_0系`<br>`FS_1系`<br>`HFS_0系`<br>`HFS_1系`<br>`SBC_CL1_0系`<br>`SBC_CL1_1系`<br>`SBC_CL2_0系`<br>`SBC_CL2_1系`<br>`SBC_CL3_0系`<br>`SBC_CL3_1系`<br>`SBC_CL4_0系`<br>`SBC_CL4_1系`<br>`SBC_CL5_0系`<br>`SBC_CL5_1系`<br>`SBC_CL6_0系`<br>`SBC_CL6_1系`<br>`HSS_CL1_0系`<br>`HSS_CL1_1系`<br>`HSS_CL2_0系`<br>`HSS_CL2_1系`<br>`HSS_CL3_0系`<br>`HSS_CL3_1系`<br>`HSS_CL4_0系`<br>`HSS_CL4_1系`<br>`HSS_CL5_0系`<br>`HSS_CL5_1系`<br>`HSS_CL6_0系`<br>`HSS_CL6_1系`<br>`SCCE.1`<br>`SCCE.2`<br>`代表EMS_0系`<br>`代表EMS_1系`<br>`同GUIの他FS_0系`<br>`同GUIの他FS_1系`<br>`同ブロックの他SSC①_0系`<br>`同ブロックの他SSC①_1系`<br>`同ブロックの他SSC②_0系`<br>`同ブロックの他SSC②_1系`<br>`同ブロックの他SSC③_0系`<br>`同ブロックの他SSC③_1系`<br>`同ブロックのISC自P①_0系`<br>`同ブロックのISC自P①_1系`<br>`同ブロックのISC自P②_0系`<br>`同ブロックのISC自P②_1系`<br>`同ブロックのISC他①_0系`<br>`同ブロックのISC他①_1系`<br>`同ブロックのISC他②_0系`<br>`同ブロックのISC他②_1系` |
## MVP仮対応済み

| プレースホルダ | 取得元 | 用途 |
| --- | --- | --- |
| `TARGET_DEVICE_HOSTNAME` | ユニット構成.xlsx の対象SBCスロット | 対象装置ホスト名 |
| `SBC_COMMAND_FLOATING_IP` | SBC.xlsx の コマンド用フローティングIPアドレス | TeraTerm接続先、コマンド欄 |
| `SBC_CALL_PROCESS_FLOATING_IP` | SBC.xlsx の `呼処理用フローティングIPアドレス` | 呼処理確認向けIP（MVP仮） |
| `SBC_MAINT_ALARM_LAN_FLOATING_IP` | SBC.xlsx の `保守アラーム用LANフローティングIPアドレス` | 保守アラームLAN向けIP（MVP仮） |
| `SBC_REMOTE_SHELL_FLOATING_IP` | SBC.xlsx の `リモートシェルコマンド用フローティングIPアドレス` | リモートシェル接続向けIP（MVP仮） |
| `SBC_NTP_FLOATING_IP` | SBC.xlsx の `NTP向けフローティングIPアドレス` | NTP確認向けIP（MVP仮） |
| `TTS_HOST` | SBC.xlsx の `TTS-Host` | 対象SBCに紐づくTTSホスト（MVP仮） |
| `TTS_IP` | SBC.xlsx の `TTS-IP` | 対象SBCに紐づくTTS IP（MVP仮） |
| `TTS_PORT` | SBC.xlsx の `TTS-Port` | 対象SBCに紐づくTTS接続ポート（MVP仮） |
| `LOGIN_USER` | case_common_values.xlsx | ログインユーザー |

## 追加候補: SBC系

| 候補名 | Access列候補 | 備考 |
| --- | --- | --- |
| `SBC_CALL_PROCESS_FLOATING_IPV6` | 呼処理用フローティングIPアドレス（ｖ６） | IPv6作業がある場合 |
| `SBC_SIGTRAN1_IP` | SIGTRAN1IPアドレス | SIGTRAN確認向け |
| `SBC_SIGTRAN2_IP` | SIGTRAN2IPアドレス | SIGTRAN確認向け |
| `SBC_ADDRESS_INFO_FLOATING_IP` | 住所情報装置向けフローティングIPアドレス | 住所情報連携向け |
| `SBC_OPERATION_DATA_TRANSFER_FLOATING_IP` | 運用データ転送用フローティングIPアドレス | 運用データ転送作業向け |
| `SBC_CL_ID` | CL_ID | 識別子出力が必要な場合 |
| `SBC_CA_ID` | CA_ID | 識別子出力が必要な場合 |
| `SBC_SOFTWARE_TYPE` | ソフト種別 | 分岐や表示制御に使う可能性あり |
| `SBC_NODE_ID` | ノードID | ノード単位の作業向け |
| `SBC_SIP_ID` | SIP-ID | SIP作業向け |
| `SBC_AR_ID` | AR-ID | AR作業向け |
| `SBC_ISC_AREA_ID` | ISCエリアID | エリア判定向け |
| `SBC_DIRECT_TERMINAL_NUMBER` | 直収端末番号 | 端末番号出力が必要な場合 |

## 追加候補: GUI系

| 候補名 | Access列候補 | 備考 |
| --- | --- | --- |
| `GUI_EMS_COMMAND_IP` | EMSコマンド用IPアドレス | GUI/EMS操作向け |
| `GUI_EMS_ALARM_IP` | EMSアラーム用IPアドレス | アラーム確認向け |
| `GUI_APL_FLOATING_IP` | APL付与のフローティングIPアドレス | APL作業向け |
| `GUI_APL_FLOATING_IP_NETMASK` | APL付与のフローティングIPアドレスのサブネットマスク | ネットマスク表示が必要な場合 |
| `GUI_BCR02_LOOPBACK_IP` | BCR02のIPアドレス(ループバックIPアドレス) | BCR02確認向け |
| `GUI_AGENT_NO` | AGENT_NO | 識別子出力が必要な場合 |
| `GUI_WEB_DEVICE_NO` | WEB_DEVICE_NO | Web装置番号が必要な場合 |

## 初期YAMLへ追加済みの候補

2026-05-14 時点で、以下は `placeholder_mapping.yml` に無効状態のMVP仮候補として追加済み。
実運用でテンプレート内に登場したものから有効化し、必要に応じて名称・説明・取得列を見直す。

| プレースホルダ | 装置 | Access列候補 |
| --- | --- | --- |
| `GUI_EMS_COMMAND_IP` | GUI | EMSコマンド用IPアドレス |
| `GUI_EMS_ALARM_IP` | GUI | EMSアラーム用IPアドレス |
| `GUI_APL_FLOATING_IP` | GUI | APL付与のフローティングIPアドレス |
| `GUI_APL_FLOATING_IP_NETMASK` | GUI | APL付与のフローティングIPアドレスのサブネットマスク |
| `GUI_BCR02_LOOPBACK_IP` | GUI | BCR02のIPアドレス(ループバックIPアドレス) |
| `HFS_MONITOR_IP` | HFS | 装置監視用 IPアドレス |
| `HFS_COMMAND_INPUT_IP` | HFS | コマンド投入用 IPアドレス |
| `HFS_NTP_IP` | HFS | NTP向け IPアドレス |
| `HFS_ALARM_SEND_IP` | HFS | アラーム送信用 IPアドレス |
| `HFS_ILO_IP` | HFS | iLO用 IPアドレス |
| `HSS_MONITOR_IP` | HSS | 装置監視用 IPアドレス |
| `HSS_COMMAND_INPUT_IP` | HSS | コマンド投入用 IPアドレス |
| `HSS_NTP_IP` | HSS | NTP向け IPアドレス |
| `HSS_ALARM_SEND_IP` | HSS | アラーム送信用 IPアドレス |
| `HSS_ILO_IP` | HSS | iLO用 IPアドレス |
| `HSS_ILO_DGW` | HSS | iLO用DGW |
| `FS_MAINT_LAN_FLOATING_IP` | FS | 保守LANフローティングIPアドレス |
| `FS_REMOTE_SHELL_FLOATING_IP` | FS | リモートシェルコマンド用フローティングIPアドレス |
| `FS_COMMAND_FLOATING_IP` | FS | コマンド用フローティングIPアドレス |
| `MSW_MAINT_MONITOR_IP` | MSW | 保守・装置監視用 |
| `RAID_MAINT_MONITOR_IP` | RAID | 保守・装置監視用 |
| `RAID_MSW_PORT_NO` | RAID | MSW収容ポート番号 |
| `SCCE_MAINT_MONITOR_IP` | SCCE | 保守・装置監視用 |
| `SCCE_VLAN_TGEX_0_4` | SCCE | VLAN「TGEX/0/4」 |
| `SCCE_UNTAG_VLAN_TGEX_0_4` | SCCE | untagVLAN「TGEX/0/4」 |

## 追加候補: FS/HFS/HSS/MSW/RAID/SCCE系

各装置ファイルは共通して `ホスト名` をキーにできる可能性がある。
装置種別ごとに、必要になった列だけプレースホルダ化する。

| 装置 | 候補列 |
| --- | --- |
| FS | 保守LANフローティングIPアドレス、リモートシェルコマンド用フローティングIPアドレス、コマンド用フローティングIPアドレス、装置監視A/B用フローティングIPアドレス |
| HFS/HSS | 装置監視用 IPアドレス、コマンド投入用 IPアドレス、NTP向け IPアドレス、アラーム送信用 IPアドレス、iLO用 IPアドレス |
| MSW/RAID/SCCE | 保守・装置監視用 |
| RAID | MSW収容ポート番号 |
| SCCE | VLAN/untagVLAN 系列 |

## 優先順位

1. 実際の案件CSテンプレートに登場する値を優先する
2. 対象ホスト名から一意に引ける値を優先する
3. 手入力を避けられる値を優先する
4. 全Access列を一括でプレースホルダ化しない
5. 追加したプレースホルダは、対応表とテストを同時に追加する

## 次に確認すること

- 添付Excelテンプレート内に、どの値が固定文字列ではなく差し替え対象として出てくるか
- SBC以外の装置を対象にした案件CS生成が必要か
- 装置種別ごとに、ホスト名をキーにしたRepositoryを増やすか


## 運用メモ

- AccessDB本体へ直接接続するのではなく、MVPでは抽出済みExcelファイルを読み込む。
- AccessDB側のテーブル・カラム・値が変わった場合は、`UNISBC` 配下相当の抽出Excelを再取得し、必要に応じてプレースホルダ対応表を見直す。
- 仮定義から正式定義へ移す際は、プレースホルダ名・取得元テーブル・取得元カラム・テストを同時に更新する。
