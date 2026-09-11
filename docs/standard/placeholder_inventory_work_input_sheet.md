# プレースホルダ一覧（工事情報入力シート対応）

## 1. この資料について

この資料は、次の情報を突き合わせて整理した一覧です。

- `apps/standard/backend/app/config/placeholder_mapping.yml`
- `apps/lab/backend/app/config/placeholder_mapping.yml`
- `C:\Users\clove\Downloads\工事入力シート.xlsx`
- シート名: `工事情報入力シート_FS`
- 対象範囲: 70行目以降

2026-08-26時点で、StandardとLabのプレースホルダ定義は同一です。

| 項目 | 件数 |
|---|---:|
| 定義総数 | 88 |
| 有効 | 82 |
| 無効 | 6 |

プレースホルダをExcelテンプレートで使用する場合は、原則として `{{プレースホルダ名}}` と記載します。

## 2. 工事情報入力シートの70行目以降との対応

装置別プレースホルダのキー列は、原則として各参照ファイルの `ホスト名` です。
`TARGET_DEVICE_HOSTNAME` はYAML定義ではなく、案件化で選択した対象装置から実行時に設定されます。

| 行 | 区分 | 工事情報入力シートの項目 | プレースホルダ | 参照ファイル | 値列 | 内部名 | 状態・備考 |
|---:|---|---|---|---|---|---|---|
| 70-72 | 工事対象 | FSクラスタ名・設置場所等 | - | ユニット構成.xlsx | 各項目 | - | 案件化の選択・絞り込みに使う情報。YAMLプレースホルダではない |
| 76 | GUI | ホスト名 | `{{TARGET_DEVICE_HOSTNAME}}` | 選択対象装置 | - | - | 実行時生成。`{{DEVICE_NAME}}` も利用可 |
| 77 | GUI | EMSコマンド用IPアドレス | `{{GUI_EMS_COMMAND_IP}}` | GUI.xlsx | EMSコマンド用IPアドレス | gui_ems_command_ip | 有効 |
| 78 | GUI | EMSアラーム用IPアドレス | `{{GUI_EMS_ALARM_IP}}` | GUI.xlsx | EMSアラーム用IPアドレス | gui_ems_alarm_ip | 有効 |
| 79 | GUI | APL付与のフローティングIPアドレス | `{{GUI_APL_FLOATING_IP}}` | GUI.xlsx | APL付与のフローティングIPアドレス | gui_apl_floating_ip | 有効 |
| 80 | GUI | iLO用 | `{{GUI_ILO_IP}}` | GUI.xlsx | iLO用 | ilo_ip | 有効 |
| 81 | GUI | TTS-Host | `{{GUI_TTS_HOST}}` | GUI.xlsx | TTS-Host | tts_host | 有効 |
| 82 | GUI | TTS-IP | `{{GUI_TTS_IP}}` | GUI.xlsx | TTS-IP | tts_ip | 有効 |
| 83 | GUI | TTS-Port | `{{GUI_TTS_PORT}}` | GUI.xlsx | TTS-Port | tts_port | 有効 |
| 87 | MSW | ホスト名 | `{{TARGET_DEVICE_HOSTNAME}}` | 選択対象装置 | - | - | 実行時生成 |
| 88 | MSW | 保守・装置監視用 | `{{MSW_MAINT_MONITOR_IP}}` | MSW.xlsx | 保守・装置監視用 | msw_maint_monitor_ip | 有効 |
| 89 | MSW | TTS-Host | `{{MSW_TTS_HOST}}` | MSW.xlsx | TTS-Host | tts_host | 有効 |
| 90 | MSW | TTS-IP | `{{MSW_TTS_IP}}` | MSW.xlsx | TTS-IP | tts_ip | 有効 |
| 91 | MSW | TTS-Port | `{{MSW_TTS_PORT}}` | MSW.xlsx | TTS-Port | tts_port | 有効 |
| 95 | RAID | ホスト名 | `{{TARGET_DEVICE_HOSTNAME}}` | 選択対象装置 | - | - | 実行時生成 |
| 96 | RAID | 保守・装置監視用 | `{{RAID_MAINT_MONITOR_IP}}` | RAID.xlsx | 保守・装置監視用 | raid_maint_monitor_ip | 有効 |
| 100 | FS | ホスト名 | `{{TARGET_DEVICE_HOSTNAME}}` | 選択対象装置 | - | - | 実行時生成 |
| 101 | FS | eth2 | `{{FS_ETH2}}` | FS.xlsx | eth2 | eth2 | 有効 |
| 102 | FS | eth0 | `{{FS_ETH0}}` | FS.xlsx | eth0 | eth0 | 有効 |
| 103 | FS | eth3 | `{{FS_ETH3}}` | FS.xlsx | eth3 | eth3 | 有効 |
| 104 | FS | eth1 | `{{FS_ETH1}}` | FS.xlsx | eth1 | eth1 | 有効 |
| 105 | FS | 保守LANフローティングIPアドレス | `{{FS_MAINT_LAN_FLOATING_IP}}` | FS.xlsx | 保守LANフローティングIPアドレス | fs_maint_lan_floating_ip | 有効 |
| 106 | FS | リモートシェルコマンド用フローティングIPアドレス | `{{FS_REMOTE_SHELL_FLOATING_IP}}` | FS.xlsx | リモートシェルコマンド用フローティングIPアドレス | fs_remote_shell_floating_ip | 有効 |
| 107 | FS | コマンド用フローティングIPアドレス | `{{FS_COMMAND_FLOATING_IP}}` | FS.xlsx | コマンド用フローティングIPアドレス | fs_command_floating_ip | 有効 |
| 108 | FS | 装置監視A用フローティングIPアドレス | `{{FS_MONITOR_A_FLOATING_IP}}` | FS.xlsx | 装置監視A用フローティングIPアドレス | monitor_a_floating_ip | 有効 |
| 109 | FS | 装置監視B用フローティングIPアドレス | `{{FS_MONITOR_B_FLOATING_IP}}` | FS.xlsx | 装置監視B用フローティングIPアドレス | monitor_b_floating_ip | 有効 |
| 110 | FS | 外部EMS一般コマンド用フローティングIPアドレス | `{{FS_EXTERNAL_EMS_COMMAND_FLOATING_IP}}` | FS.xlsx | 外部EMS一般コマンド用フローティングIPアドレス | external_ems_command_floating_ip | 有効 |
| 111 | FS | 外部EMSアラーム用フローティングIPアドレス | `{{FS_EXTERNAL_EMS_ALARM_FLOATING_IP}}` | FS.xlsx | 外部EMSアラーム用フローティングIPアドレス | external_ems_alarm_floating_ip | 有効 |
| 112 | FS | 保守LANフローティングIPアドレス（SBY用） | `{{FS_MAINT_LAN_FLOATING_IP_SBY}}` | FS.xlsx | 保守LANフローティングIPアドレス（SBY用） | maint_lan_floating_ip_sby | 有効 |
| 116 | HFS | ホスト名 | `{{TARGET_DEVICE_HOSTNAME}}` | 選択対象装置 | - | - | 実行時生成 |
| 117 | HFS | 装置監視用 IPアドレス | `{{HFS_MONITOR_IP}}` | HFS.xlsx | 装置監視用 IPアドレス | hfs_monitor_ip | 有効 |
| 118 | HFS | コマンド投入用 IPアドレス | `{{HFS_COMMAND_INPUT_IP}}` | HFS.xlsx | コマンド投入用 IPアドレス | hfs_command_input_ip | 有効 |
| 119 | HFS | NTP向け IPアドレス | `{{HFS_NTP_IP}}` | HFS.xlsx | NTP向け IPアドレス | hfs_ntp_ip | 有効 |
| 120 | HFS | アラーム送信用 IPアドレス | `{{HFS_ALARM_SEND_IP}}` | HFS.xlsx | アラーム送信用 IPアドレス | hfs_alarm_send_ip | 有効 |
| 121 | HFS | ホスト-ゲスト用 IPアドレス | `{{HFS_HOST_GUEST_IP}}` | HFS.xlsx | ホスト-ゲスト用 IPアドレス | host_guest_ip | 有効 |
| 122 | HFS | iLO用 IPアドレス | `{{HFS_ILO_IP}}` | HFS.xlsx | iLO用 IPアドレス | hfs_ilo_ip | 有効 |
| 123 | HFS | TTS-Host | `{{HFS_TTS_HOST}}` | HFS.xlsx | TTS-Host | tts_host | 有効 |
| 124 | HFS | TTS-IP | `{{HFS_TTS_IP}}` | HFS.xlsx | TTS-IP | tts_ip | 有効 |
| 125 | HFS | TTS-Port | `{{HFS_TTS_PORT}}` | HFS.xlsx | TTS-Port | tts_port | 有効 |
| 129 | SSC/ISC | ホスト名 | `{{TARGET_DEVICE_HOSTNAME}}` | 選択対象装置 | - | - | 実行時生成 |
| 130 | SSC/ISC | eth0 | `{{SBC_ETH0}}` | SBC.xlsx | eth0 | eth0 | 有効 |
| 131 | SSC/ISC | eth1 | `{{SBC_ETH1}}` | SBC.xlsx | eth1 | eth1 | 有効 |
| 132 | SSC/ISC | eth2 | `{{SBC_ETH2}}` | SBC.xlsx | eth2 | eth2 | 有効 |
| 133 | SSC/ISC | eth3 | `{{SBC_ETH3}}` | SBC.xlsx | eth3 | eth3 | 有効 |
| 134 | SSC/ISC | 呼処理用フローティングIPアドレス | `{{SBC_CALL_PROCESS_FLOATING_IP}}` | SBC.xlsx | 呼処理用フローティングIPアドレス | call_process_floating_ip | 有効 |
| 135 | SSC/ISC | 呼処理用フローティングIPアドレス（v6） | `{{SBC_CALL_PROCESS_FLOATING_IPV6}}` | SBC.xlsx | 呼処理用フローティングIPアドレス（ｖ６） | call_process_floating_ipv6 | 有効 |
| 136 | SSC/ISC | コマンド用フローティングIPアドレス | `{{SBC_COMMAND_FLOATING_IP}}` | SBC.xlsx | コマンド用フローティングIPアドレス | command_floating_ip | 有効。`{{NW_ADDRESS}}` も利用可 |
| 137 | SSC/ISC | 保守アラーム用LANフローティングIPアドレス | `{{SBC_MAINT_ALARM_LAN_FLOATING_IP}}` | SBC.xlsx | 保守アラーム用LANフローティングIPアドレス | maint_alarm_lan_floating_ip | 有効 |
| 138 | SSC/ISC | リモートシェルコマンド用フローティングIPアドレス | `{{SBC_REMOTE_SHELL_FLOATING_IP}}` | SBC.xlsx | リモートシェルコマンド用フローティングIPアドレス | remote_shell_floating_ip | 有効 |
| 139 | SSC/ISC | NTP向けフローティングIPアドレス | `{{SBC_NTP_FLOATING_IP}}` | SBC.xlsx | NTP向けフローティングIPアドレス | ntp_floating_ip | 有効 |
| 140 | SSC/ISC | 住所情報装置向けフローティングIPアドレス | `{{SBC_ADDRESS_INFO_DEVICE_FLOATING_IP}}` | SBC.xlsx | 住所情報装置向けフローティングIPアドレス | address_info_device_floating_ip | 有効 |
| 141 | SSC/ISC | 運用データ転送用フローティングIPアドレス | `{{SBC_OPERATION_DATA_TRANSFER_FLOATING_IP}}` | SBC.xlsx | 運用データ転送用フローティングIPアドレス | operation_data_transfer_floating_ip | 有効 |
| 142 | SSC/ISC | CA_ID | `{{SBC_CA_ID}}` | SBC.xlsx | CA_ID | ca_id | 有効 |
| 143 | SSC/ISC | CL_ID | `{{SBC_CL_ID}}` | SBC.xlsx | CL_ID | cl_id | 有効 |
| 147 | HSS | ホスト名 | `{{TARGET_DEVICE_HOSTNAME}}` | 選択対象装置 | - | - | 実行時生成 |
| 148 | HSS | 装置監視用 IPアドレス | `{{HSS_MONITOR_IP}}` | HSS.xlsx | 装置監視用 IPアドレス | hss_monitor_ip | 有効 |
| 149 | HSS | コマンド投入用 IPアドレス | `{{HSS_COMMAND_INPUT_IP}}` | HSS.xlsx | コマンド投入用 IPアドレス | hss_command_input_ip | 有効 |
| 150 | HSS | NTP向け IPアドレス | `{{HSS_NTP_IP}}` | HSS.xlsx | NTP向け IPアドレス | hss_ntp_ip | 有効 |
| 151 | HSS | アラーム送信用 IPアドレス | `{{HSS_ALARM_SEND_IP}}` | HSS.xlsx | アラーム送信用 IPアドレス | hss_alarm_send_ip | 有効 |
| 152 | HSS | ホスト-ゲスト用 IPアドレス | `{{HSS_HOST_GUEST_IP}}` | HSS.xlsx | ホスト-ゲスト用 IPアドレス | host_guest_ip | 有効 |
| 153 | HSS | iLO用 IPアドレス | `{{HSS_ILO_IP}}` | HSS.xlsx | iLO用 IPアドレス | hss_ilo_ip | 有効 |
| 154 | HSS | TTS-Host | `{{HSS_TTS_HOST}}` | HSS.xlsx | TTS-Host | tts_host | 有効 |
| 155 | HSS | TTS-IP | `{{HSS_TTS_IP}}` | HSS.xlsx | TTS-IP | tts_ip | 有効 |
| 156 | HSS | TTS-Port | `{{HSS_TTS_PORT}}` | HSS.xlsx | TTS-Port | tts_port | 有効 |
| 160 | SCCE | ホスト名 | `{{TARGET_DEVICE_HOSTNAME}}` | 選択対象装置 | - | - | 実行時生成 |
| 161 | SCCE | 保守・装置監視用 | `{{SCCE_MAINT_MONITOR_IP}}` | SCCE.xlsx | 保守・装置監視用 | scce_maint_monitor_ip | 有効 |
| 162 | SCCE | TTS-Host | `{{SCCE_TTS_HOST}}` | SCCE.xlsx | TTS-Host | tts_host | 有効 |
| 163 | SCCE | TTS-IP | `{{SCCE_TTS_IP}}` | SCCE.xlsx | TTS-IP | tts_ip | 有効 |
| 164 | SCCE | TTS-Port | `{{SCCE_TTS_PORT}}` | SCCE.xlsx | TTS-Port | tts_port | 有効 |
| 168-172 | 代表EMS | ホスト名、EMS用IP、APL、iLO | GUI系プレースホルダを再利用 | GUI.xlsx | 各GUI列 | 各GUI内部名 | GUI行76-80と同じ定義を使用 |
| 176-178 | 同ブロックの他SSC | ホスト名、呼処理IPv4/IPv6 | SBC系プレースホルダを再利用 | SBC.xlsx | 各SBC列 | 各SBC内部名 | SSC/ISC行129、134、135と同じ定義を使用 |
| 182-184 | 同ブロックのISC自P | ホスト名、呼処理IPv4/IPv6 | SBC系プレースホルダを再利用 | SBC.xlsx | 各SBC列 | 各SBC内部名 | SSC/ISC行129、134、135と同じ定義を使用 |
| 188-190 | 同ブロックのISC他 | ホスト名、呼処理IPv4/IPv6 | SBC系プレースホルダを再利用 | SBC.xlsx | 各SBC列 | 各SBC内部名 | SSC/ISC行129、134、135と同じ定義を使用 |
| 194-195 | 同GUIの他FS | ホスト名、外部EMSアラーム用IP | FS系プレースホルダを再利用 | FS.xlsx | 各FS列 | 各FS内部名 | FS行100、111と同じ定義を使用 |

## 3. SBCから関連HSSを参照するTTSプレースホルダ

次の3件は、対象装置がSBCの場合に、同じCL・系のHSSを特定して値を取得する定義です。
工事情報入力シートの単一行へ直接対応するというより、案件化時の装置間リレーションを使います。

| プレースホルダ | 対象装置 | 実際の参照先 | キー列 | 値列 | 内部名 | 状態 |
|---|---|---|---|---|---|---|
| `{{TTS_HOST}}` | SBC | HSS.xlsx | ホスト名 | TTS-Host | tts_host | 有効 |
| `{{TTS_IP}}` | SBC | HSS.xlsx | ホスト名 | TTS-IP | tts_ip | 有効 |
| `{{TTS_PORT}}` | SBC | HSS.xlsx | ホスト名 | TTS-Port | tts_port | 有効 |

## 4. 共通値プレースホルダ

共通値は `case_common_values.xlsx` を参照します。
キー列は `key`、値列は `value` で、キー値にはプレースホルダ名と同じ文字列を使います。

| プレースホルダ | 内部名 | 用途 | 状態 |
|---|---|---|---|
| `{{LOGIN_USER}}` | login_user | ログインユーザー名 | 有効 |
| `{{LOGIN_PASSWORD}}` | login_password | ログインパスワード | 有効 |
| `{{PRIVILEGED_PASSWORD}}` | privileged_password | 特権モードパスワード | 有効 |
| `{{TERATERM_LOG_FILE_NAME}}` | teraterm_log_file_name | TeraTermログファイル名 | 有効 |
| `{{TERATERM_LOG_FOLDER_NOTE}}` | teraterm_log_folder_note | TeraTermログ保存先の注意書き | 有効 |
| `{{TTS_SERVICE}}` | tts_service | TTS接続サービス名 | 有効 |
| `{{TTS_MENU_HOSTNAME}}` | tts_menu_hostname | TTSメニューに表示されるホスト名 | 有効 |
| `{{TTS_SHOW_TTY_COMMAND}}` | tts_show_tty_command | TTY設定表示コマンド | 有効 |
| `{{TTS_SET_TTY_BAUD_COMMAND}}` | tts_set_tty_baud_command | TTYボーレート設定コマンド | 有効 |
| `{{TTS_TARGET_PORT_PRIMARY}}` | tts_target_port_primary | 第1対象ポート | 有効 |
| `{{TTS_TARGET_PORT_SECONDARY}}` | tts_target_port_secondary | 第2対象ポート | 有効 |
| `{{TTS_EXPECTED_BAUD_PRIMARY}}` | tts_expected_baud_primary | 第1期待ボーレート | 有効 |
| `{{TTS_EXPECTED_BAUD_SECONDARY}}` | tts_expected_baud_secondary | 第2期待ボーレート | 有効 |
| `{{CONFIG_SHOW_COMMAND}}` | config_show_command | 稼働中コンフィグ表示コマンド | 有効 |
| `{{STARTUP_CONFIG_SHOW_COMMAND}}` | startup_config_show_command | 起動時コンフィグ表示コマンド | 有効 |
| `{{CONFIG_OUTPUT_FORMAT_COMMAND}}` | config_output_format_command | コンフィグ表示形式変更コマンド | 有効 |
| `{{CONFIG_SAVE_COMMAND}}` | config_save_command | コンフィグ保存コマンド | 有効 |
| `{{CONFIRM_YES}}` | confirm_yes | 確認プロンプトへのYes応答 | 有効 |
| `{{WORK_CONTACT_PHONE}}` | work_contact_phone | 工事連絡先電話番号 | 有効 |

`{{USER}}` は `{{LOGIN_USER}}` へ変換される互換名です。

## 5. 現在無効の候補プレースホルダ

次の6件はYAMLに定義されていますが、現在は `enabled: false` です。
Excelテンプレートに記載しても、通常の値解決対象にはなりません。

| プレースホルダ | 装置種別 | 参照ファイル | 値列 | 内部名 |
|---|---|---|---|---|
| `{{GUI_APL_FLOATING_IP_NETMASK}}` | GUI | GUI.xlsx | APL付与のフローティングIPアドレスのサブネットマスク | gui_apl_floating_ip_netmask |
| `{{GUI_BCR02_LOOPBACK_IP}}` | GUI | GUI.xlsx | BCR02のIPアドレス(ループバックIPアドレス) | gui_bcr02_loopback_ip |
| `{{HSS_ILO_DGW}}` | HSS | HSS.xlsx | iLO用DGW | hss_ilo_dgw |
| `{{RAID_MSW_PORT_NO}}` | RAID | RAID.xlsx | MSW収容ポート番号 | raid_msw_port_no |
| `{{SCCE_VLAN_TGEX_0_4}}` | SCCE | SCCE.xlsx | VLAN「TGEX/0/4」 | scce_vlan_tgex_0_4 |
| `{{SCCE_UNTAG_VLAN_TGEX_0_4}}` | SCCE | SCCE.xlsx | untagVLAN「TGEX/0/4」 | scce_untag_vlan_tgex_0_4 |

## 6. 互換プレースホルダ

次の名前は既存テンプレートとの互換性維持のため、生成処理で正式名へ読み替えられます。

| 互換名 | 正式な解決先 | 備考 |
|---|---|---|
| `{{DEVICE_NAME}}` | `{{TARGET_DEVICE_HOSTNAME}}` | 対象装置のホスト名 |
| `{{NW_ADDRESS}}` | `{{SBC_COMMAND_FLOATING_IP}}` | 過去の仮名。新規テンプレートでは正式名を推奨 |
| `{{USER}}` | `{{LOGIN_USER}}` | 過去の短縮名 |

## 7. 運用上の注意

- 行番号は、2026-08-26時点の `工事入力シート.xlsx` を基準にしています。Excelへ行を追加・削除すると行番号は変わります。
- 項目名と `value_column` は完全一致が基本です。全角・半角、空白、括弧の違いにも注意してください。
- `source_column` はアプリ内部で扱う名前であり、Excelテンプレートへ記載するプレースホルダ名とは異なります。
- 同じ値列名でも装置種別が異なる場合は、`GUI_TTS_HOST`、`HFS_TTS_HOST` のように装置種別を含む別プレースホルダとして扱います。
- 新しいテンプレートでは互換名より、正式なプレースホルダ名を使用してください。
