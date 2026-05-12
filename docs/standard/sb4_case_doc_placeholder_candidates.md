# SB4 案件CS プレースホルダ候補メモ

## 目的

`CASE_DOC_MASTER_SOURCE=export_file` で仮のAccess抽出ファイルを読み込み、案件CS生成まで確認した結果をもとに、今後追加候補となるプレースホルダを整理する。

## 現在対応済み

| プレースホルダ | 取得元 | 用途 |
| --- | --- | --- |
| `TARGET_DEVICE_HOSTNAME` | ユニット構成.xlsx の対象SBCスロット | 対象装置ホスト名 |
| `SBC_COMMAND_FLOATING_IP` | SBC.xlsx の コマンド用フローティングIPアドレス | TeraTerm接続先、コマンド欄 |
| `LOGIN_USER` | case_common_values.xlsx | ログインユーザー |

## 追加候補: 接続・TTS系

| 候補名 | 取得元候補 | 備考 |
| --- | --- | --- |
| `TTS_HOST` | GUI/HFS/HSS/MSW/RAID/SCCE.xlsx の `TTS-Host` | 対象装置や作業端末接続に必要なら追加 |
| `TTS_IP` | GUI/HFS/HSS/MSW/RAID/SCCE.xlsx の `TTS-IP` | IP指定が必要な作業向け |
| `TTS_PORT` | GUI/HFS/HSS/MSW/RAID/SCCE.xlsx の `TTS-Port` | Telnet/SSHポート指定向け |

## 追加候補: SBC系

| 候補名 | Access列候補 | 備考 |
| --- | --- | --- |
| `SBC_CALL_PROCESS_FLOATING_IP` | 呼処理用フローティングIPアドレス | 呼処理確認で必要になる可能性あり |
| `SBC_CALL_PROCESS_FLOATING_IPV6` | 呼処理用フローティングIPアドレス（ｖ６） | IPv6作業がある場合 |
| `SBC_SIGTRAN1_IP` | SIGTRAN1IPアドレス | SIGTRAN確認向け |
| `SBC_SIGTRAN2_IP` | SIGTRAN2IPアドレス | SIGTRAN確認向け |
| `SBC_REMOTE_SHELL_FLOATING_IP` | リモートシェルコマンド用フローティングIPアドレス | リモートシェル作業向け |
| `SBC_NTP_FLOATING_IP` | NTP向けフローティングIPアドレス | 時刻同期確認向け |
| `SBC_MAINT_ALARM_LAN_FLOATING_IP` | 保守アラーム用LANフローティングIPアドレス | 監視/アラーム系 |
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

## 追加候補: FS/HFS/HSS/MSW/RAID/SCCE系

各装置ファイルは共通して `ホスト名` をキーにできる可能性がある。
装置種別ごとに、必要になった列だけプレースホルダ化する。

| 装置 | 候補列 |
| --- | --- |
| FS | 保守LANフローティングIPアドレス、リモートシェルコマンド用フローティングIPアドレス、コマンド用フローティングIPアドレス、装置監視A/B用フローティングIPアドレス |
| HFS/HSS | 装置監視用 IPアドレス、コマンド投入用 IPアドレス、NTP向け IPアドレス、アラーム送信用 IPアドレス、iLO用 IPアドレス |
| MSW/RAID/SCCE | 保守・装置監視用、TTS-Host、TTS-IP、TTS-Port |
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
- `TTS-Host` / `TTS-IP` / `TTS-Port` を対象SBCからどう決めるか
- SBC以外の装置を対象にした案件CS生成が必要か
- 装置種別ごとに、ホスト名をキーにしたRepositoryを増やすか
