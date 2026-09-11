# Standardオフラインサーバー IPアドレス・SSH初期設定手順書

## 1. 目的

Standardのオフライン導入前に、Ubuntu Serverへ固定IPアドレスとSSHを設定し、作業PCから安全に接続できる状態にする。

対象OSはUbuntu Server 24.04 LTS、CPUアーキテクチャは`amd64` / `x86_64`とする。

## 2. 作業時の注意

> [!WARNING]
> IPアドレス設定を変更するとSSH接続が切れる。初回設定は、サーバーの物理コンソール、仮想マシンコンソール、iLO、iDRACなど、ネットワークに依存しない管理画面から実施する。

- 設定前に、使用するIPアドレスがほかの機器と重複していないことを確認する
- NIC名、サブネット、ゲートウェイ、DNSは実環境の値を確認する
- NetplanのYAMLではタブを使用せず、半角スペースでインデントする
- SSH設定変更後は、現在の接続を閉じる前に別ターミナルから再接続を確認する
- パスワードを手順書やリポジトリへ記載しない

## 3. 事前に決める値

次の項目をネットワーク管理者へ確認する。

| 項目 | 設定例 | 必須条件 |
| --- | --- | --- |
| hostname | `procedure-db-standard` | ネットワーク内で重複しないこと |
| IPv4アドレス | `10.58.143.28` | 予約済みの未使用アドレスであること |
| プレフィックス長 | `/24` | 実際のサブネットに合わせる |
| デフォルトゲートウェイ | `10.58.143.1` | 別セグメントと通信する場合に必要 |
| DNSサーバー | 社内DNSのIPアドレス | ホスト名解決が必要な場合に設定 |
| NIC名 | 例: `enp0s25` | サーバー上で確認する |
| SSHユーザー | `user` | sudoを実行できること |
| 接続元ネットワーク | ネットワーク管理者の指定CIDR | SSH・WebUIの許可範囲に使用 |

作業PCとサーバーが同じサブネット内だけで通信し、外部や別VLANへ通信しない場合、ゲートウェイとDNSを省略できる。異なるネットワークからSSH接続する場合は、正しいゲートウェイとルーティング設定が必要になる。

## 4. OSと現在状態を確認する

サーバーのコンソールで実行する。

```bash
cat /etc/os-release
uname -m
ip -br link
ip -br address
ip route
ls -la /etc/netplan
```

次を確認する。

- `VERSION_ID="24.04"`である
- `uname -m`が`x86_64`である
- `ip -br link`で有線NIC名を確認できる
- 使用するNICが`UP`である
- `/etc/netplan`に既存のYAMLファイルがあるか確認できる

以降の例にある`enp0s25`は、実際に確認したNIC名へ置き換える。

### 4.1 `nano`の保存と終了

この手順書では設定ファイルの編集に`nano`を使用する。画面下部に表示される`^`は`Ctrl`キーを表す。たとえば`^O`は`Ctrl + O`である。

編集内容を保存して終了する場合:

1. `Ctrl + O`を押す
2. 保存するファイル名が表示されたら`Enter`を押す
3. `Ctrl + X`を押して終了する

先に終了操作を行う場合:

1. `Ctrl + X`を押す
2. 保存確認が表示されたら`Y`を押す
3. ファイル名を確認して`Enter`を押す

変更を保存せずに終了する場合:

1. `Ctrl + X`を押す
2. 保存確認が表示されたら`N`を押す

| 操作 | キー |
| --- | --- |
| 保存 | `Ctrl + O`、`Enter` |
| 終了 | `Ctrl + X` |
| 保存して終了 | `Ctrl + X`、`Y`、`Enter` |
| 保存せず終了 | `Ctrl + X`、`N` |

## 5. hostnameを設定する

```bash
sudo hostnamectl set-hostname procedure-db-standard
hostnamectl
```

`/etc/hosts`の`127.0.1.1`にもhostnameを設定する。

```bash
sudo nano /etc/hosts
```

例:

```text
127.0.0.1 localhost
127.0.1.1 procedure-db-standard
```

既存のIPv6行は削除しない。

## 6. Netplan設定をバックアップする

```bash
sudo mkdir -p /root/netplan-backup
sudo cp -a /etc/netplan/. /root/netplan-backup/
sudo ls -la /root/netplan-backup
```

既存ファイルの内容を確認する。

```bash
sudo grep -R . /etc/netplan
```

## 7. 固定IPアドレスを設定する

### 7.1 同一サブネット内だけで使用する場合

既存のNetplanファイルを編集する。ファイル名は環境により異なる。

```bash
sudo nano /etc/netplan/99-standard-static.yaml
```

例:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s25:
      dhcp4: false
      addresses:
        - 10.58.143.28/24
```

### 7.2 デフォルトゲートウェイを使用する場合

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s25:
      dhcp4: false
      addresses:
        - 10.58.143.28/24
      routes:
        - to: default
          via: 10.58.143.1
```

社内DNSが必要な場合のみ、`enp0s25`配下へ次の設定を追加する。

```yaml
      nameservers:
        addresses:
          - <dns-server-ip>
```

`<dns-server-ip>`は、実際の社内DNSのIPアドレスへ必ず置き換える。値が未確定の場合は`nameservers`を設定しない。オフライン環境では、到達できないパブリックDNSを設定しない。

### 7.3 既存設定との重複を確認する

Netplanは`/etc/netplan`にある複数のYAMLファイルを統合する。同じ`enp0s25`を複数ファイルで定義したままにせず、最終的に有効な定義を1つにする。

最初に、設定ファイルと`enp0s25`の定義箇所を確認する。

```bash
sudo ls -la /etc/netplan
sudo grep -R -nE 'enp0s25|dhcp4|addresses|routes' /etc/netplan
```

#### パターンA: `enp0s25`の既存定義がない

重複はないため、`/etc/netplan/99-standard-static.yaml`をそのまま使用する。

#### パターンB: 既存ファイルが`enp0s25`だけを定義している

既存ファイルを編集し、`99-standard-static.yaml`は使用しない方法が分かりやすい。

1. 既存ファイルをバックアップする
2. 既存ファイル内の`dhcp4: true`を`dhcp4: false`へ変更する
3. `addresses`へ`10.58.143.28/24`を設定する
4. 作成済みの`99-standard-static.yaml`は拡張子を変えて無効化する

次は既存ファイルが`00-installer-config.yaml`だった場合の例である。実際のファイル名へ置き換える。

```bash
sudo cp -a /etc/netplan/00-installer-config.yaml \
  /root/netplan-backup/00-installer-config.yaml.before-static
sudo nano /etc/netplan/00-installer-config.yaml
sudo mv /etc/netplan/99-standard-static.yaml \
  /etc/netplan/99-standard-static.yaml.disabled
```

`99-standard-static.yaml`が存在しない場合、最後の`mv`は実行しない。

既存ファイルの設定例:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s25:
      dhcp4: false
      addresses:
        - 10.58.143.28/24
```

#### パターンC: 既存ファイルにほかのNICも定義されている

ファイル全体を無効化すると、ほかのNICも停止する。この場合は既存ファイルを残し、`enp0s25`のブロックだけを編集する。`99-standard-static.yaml`には`enp0s25`を重ねて定義しない。

編集前後で、ほかのNICの定義が変わっていないことを確認する。

```bash
sudo cp -a /etc/netplan /root/netplan-before-enp0s25-change
EXISTING_FILE="00-installer-config.yaml"
sudo nano "/etc/netplan/$EXISTING_FILE"
sudo diff -ru /root/netplan-before-enp0s25-change /etc/netplan || true
```

`EXISTING_FILE`は実際のファイル名へ置き換える。

#### パターンD: 複数ファイルに`enp0s25`が定義されている

残すファイルを1つ決め、それ以外のファイルは削除せず、`.yaml.disabled`へ名前を変更する。Netplanが読み込む拡張子は`.yaml`であるため、名前を変更すると設定対象外になる。

次は`50-cloud-init.yaml`を無効化し、`99-standard-static.yaml`を残す場合の例である。

```bash
sudo cp -a /etc/netplan/50-cloud-init.yaml \
  /root/netplan-backup/50-cloud-init.yaml.before-disable
sudo mv /etc/netplan/50-cloud-init.yaml \
  /etc/netplan/50-cloud-init.yaml.disabled
```

対象ファイルにほかのNICが含まれる場合は、この方法を使用せずパターンCに従う。

#### cloud-init管理の設定が重複している場合

既存ファイル名に`cloud-init`が含まれ、ファイル内に「変更が再生成される」という注意書きがある場合は、運用担当者とcloud-initの扱いを確認する。

cloud-initによるネットワーク再生成を無効化し、`99-standard-static.yaml`を使用する場合は、次のファイルを作成する。

```bash
sudo nano /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
```

```yaml
network: {config: disabled}
```

続いて、`enp0s25`を定義している既存のcloud-init生成YAMLを、前述のパターンDと同様にバックアップして`.yaml.disabled`へ変更する。無効化設定だけを作っても既存YAMLは残るため、重複は解消されない。

#### 重複解消後の確認

再度検索し、有効な`.yaml`ファイルで`enp0s25`を定義している箇所が1つだけであることを確認する。

```bash
sudo grep -R -nE --include='*.yaml' \
  'enp0s25|dhcp4|addresses|routes' /etc/netplan
sudo netplan get
sudo netplan generate
```

`netplan generate`でエラーがないことを確認してから、コンソール上で`sudo netplan try`へ進む。

#### IPアドレス自体の重複も確認する

設定ファイルの重複とは別に、`10.58.143.28`がほかの機器へ割り当てられていないことをネットワーク管理者へ確認する。ping応答がないだけでは未使用とは断定できないため、管理台帳やDHCPの予約状況を優先する。

### 7.4 権限と構文を確認する

```bash
sudo chmod 600 /etc/netplan/*.yaml
sudo netplan generate
```

エラーが表示された場合は適用せず、YAMLのNIC名、コロン、インデントを修正する。

### 7.5 設定を試行して適用する

コンソールから実行する。

```bash
sudo netplan try
```

通信できることを確認して設定を承認する。承認できない場合は一定時間後に元の設定へ戻る。

続けて明示的に適用する。

```bash
sudo netplan apply
```

## 8. IPアドレスを確認する

```bash
ip -br address
ip route
GATEWAY_IP="10.58.143.1"
ping -c 4 "$GATEWAY_IP"
```

`ip route`に、少なくとも次の経路が表示されることを確認する。

```text
default via 10.58.143.1 dev enp0s25
10.58.143.0/24 dev enp0s25 proto kernel scope link src 10.58.143.28
```

ゲートウェイを使用しない構成では、最後のping確認は不要である。代わりに同一サブネット上の作業PCや疎通確認用端末へpingする。

作業PCのPowerShellから確認する。

```powershell
ping 10.58.143.28
Test-NetConnection 10.58.143.28 -Port 22
```

この時点ではSSH未設定の場合があるため、TCP 22番の確認失敗は次章で対応する。

## 9. sudoユーザーを確認する

Ubuntu Serverインストール時に作成したユーザーを使用する場合:

```bash
id user
groups user
sudo -v
```

`groups user`の結果に`sudo`が含まれることを確認する。

ユーザーが存在しない場合は、コンソールから作成する。

```bash
sudo adduser user
sudo usermod -aG sudo user
id user
```

## 10. OpenSSH Serverを設定する

### 10.1 インストール状態を確認する

```bash
dpkg-query -W openssh-server 2>/dev/null || echo "openssh-serverは未導入です"
```

未導入の場合、推奨方法はUbuntu Serverインストール時に`Install OpenSSH server`を選択することである。

すでにオフライン状態で未導入の場合は、導入先と同じUbuntuバージョン・CPUアーキテクチャ向けの`openssh-server`と依存`.deb`一式を別途持ち込む必要がある。Standardオフライン配布物にはOpenSSH用`.deb`は含まれない。

オンライン接続可能な段階で導入できる場合:

```bash
sudo apt update
sudo apt install -y openssh-server
```

### 10.2 SSHサービスを有効化する

```bash
sudo systemctl enable --now ssh.service
sudo systemctl status ssh.service --no-pager
```

`active (running)`であることを確認する。

### 10.3 SSH設定をバックアップする

```bash
sudo cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.before-standard
```

### 10.4 PoC用の認証設定を作成する

初期導入でパスワード認証を使用する場合は、設定スニペットを作成する。

```bash
sudo nano /etc/ssh/sshd_config.d/00-procedure-db.conf
```

```text
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication yes
```

本番運用では公開鍵認証へ切り替え、パスワード認証を無効化することを推奨する。

### 10.5 構文確認後に再起動する

```bash
sudo sshd -t
sudo systemctl restart ssh.service
sudo systemctl is-active ssh.service
sudo ss -lntp | grep ':22 '
```

`sshd -t`でエラーが出た場合は再起動せず、設定を修正する。

## 11. ファイアウォールを設定する

状態を確認する。

```bash
command -v ufw || echo "UFWは未導入です"
sudo ufw status verbose
```

UFWが未導入の場合、Standardオフライン配布物だけでは追加導入されない。社内のファイアウォールまたは別途準備したUFWを使用する。

UFWを使用できる場合は、先にSSHを許可する。次のネットワークアドレスは実環境へ合わせる。

```bash
ALLOWED_NETWORK="<allowed-network-cidr>"
sudo ufw allow from "$ALLOWED_NETWORK" to any port 22 proto tcp
sudo ufw allow from "$ALLOWED_NETWORK" to any port 3000 proto tcp
sudo ufw enable
sudo ufw status numbered
```

StandardではWebUIのTCP 3000番だけをLANへ公開する。APIの8000番とPostgreSQLの5432番はlocalhost限定のため、外部向けに許可しない。

社内ファイアウォールやVLAN ACLで制御する場合は、サーバー上のUFWと設定が矛盾しないようネットワーク管理者へ確認する。

## 12. 作業PCからSSH接続を確認する

PowerShellで実行する。

```powershell
Test-NetConnection 10.58.143.28 -Port 22
ssh user@10.58.143.28
```

初回接続時はホスト鍵のフィンガープリントを、サーバーコンソール上の次の結果と照合する。

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

サーバーを再インストールし、同じIPアドレスを再利用した場合にホスト鍵エラーが出ることがある。再インストールしたことを確認したうえで、作業PCから古い記録を削除する。

```powershell
ssh-keygen -R 10.58.143.28
```

接続後、sudoを確認する。

```bash
whoami
sudo -v
hostname
hostname -I
```

## 13. 公開鍵認証へ切り替える場合

作業PCに鍵がない場合はPowerShellで作成する。

```powershell
ssh-keygen -t ed25519
```

公開鍵をサーバーへ登録する。

```powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh user@10.58.143.28 "umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
```

別のPowerShellを開き、公開鍵で接続できることを確認する。

```powershell
ssh user@10.58.143.28
```

公開鍵接続を確認してから、必要に応じて`/etc/ssh/sshd_config.d/00-procedure-db.conf`を次のように変更する。

```text
PasswordAuthentication no
```

変更後は必ず構文を確認する。

```bash
sudo sshd -t
sudo systemctl restart ssh.service
```

## 14. IP・SSH以外に設定する項目

### 14.1 必須

| 項目 | 確認内容 |
| --- | --- |
| OS・CPU | Ubuntu 24.04、`x86_64`である |
| sudoユーザー | SSHユーザーがsudoを実行できる |
| hostname | 社内ネットワーク内で重複しない |
| ストレージ | `/`に最低10 GiB、PoCでは20 GiB以上の空きを推奨 |
| メモリ | PoCでは4 GiB以上を推奨 |
| CPU | PoCでは2 vCPU以上を推奨 |
| ポート | `3000`、`8000`、`5432`が未使用である |
| 資材搬入 | SCP、SFTP、USBなど社内規程に沿う搬入方法がある |

### 14.2 推奨

| 項目 | 確認内容 |
| --- | --- |
| 時刻・タイムゾーン | ログ時刻を合わせるため`Asia/Tokyo`へ設定する |
| NTP | 社内NTPがある場合は同期先を設定する |
| ファイアウォール | SSH 22番とWebUI 3000番だけを必要な接続元へ許可する |
| 名前解決 | 必要に応じて社内DNSへhostnameを登録する |
| バックアップ | Netplan、SSH設定、DBデータの保管方法を決める |
| コンソール | SSH障害時に利用できる管理経路を確保する |

タイムゾーンの設定例:

```bash
sudo timedatectl set-timezone Asia/Tokyo
timedatectl
```

空き容量とポートの確認例:

```bash
df -h /
free -h
nproc
ss -lnt | grep -E ':(3000|8000|5432)[[:space:]]' || echo "Standard用ポートは未使用です"
```

## 15. Standard導入前チェックリスト

- [ ] Ubuntu 24.04、`x86_64`である
- [ ] 固定IPアドレスに重複がない
- [ ] 再起動後も固定IPアドレスが維持される
- [ ] hostnameが設定されている
- [ ] 作業PCからTCP 22番へ接続できる
- [ ] `user`でSSHログインできる
- [ ] `user`がsudoを実行できる
- [ ] SSHホスト鍵を確認した
- [ ] TCP 3000番を必要な接続元から利用できる
- [ ] TCP 8000番と5432番を外部公開していない
- [ ] Standard用ポートが未使用である
- [ ] 時刻とタイムゾーンが正しい
- [ ] ディスク、メモリ、CPUの必要量を満たしている
- [ ] オフライン配布物の搬入方法が決まっている

すべて確認できたら、`standard_docker_cli_server_offline_hands_on_guide.md`へ進む。

## 16. 設定を戻す場合

Netplan設定を戻す場合は、サーバーコンソールから実行する。

```bash
sudo rm -f /etc/netplan/99-standard-static.yaml
sudo rm -f /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
sudo cp -a /root/netplan-backup/. /etc/netplan/
sudo netplan generate
sudo netplan apply
```

SSH設定を戻す場合:

```bash
sudo rm -f /etc/ssh/sshd_config.d/00-procedure-db.conf
sudo cp -a /etc/ssh/sshd_config.before-standard /etc/ssh/sshd_config
sudo sshd -t
sudo systemctl restart ssh.service
```

## 17. 参考資料

- [Ubuntu Server: Configuring networks](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/)
- [Ubuntu Server: OpenSSH server](https://documentation.ubuntu.com/server/how-to/security/openssh-server/)
- [Ubuntu Server: User management](https://documentation.ubuntu.com/server/how-to/security/user-management/)
- [Netplan tutorial](https://netplan.readthedocs.io/en/stable/netplan-tutorial/)
