# 🦙 Local LLM Server (Ollama + Nginx + Docker)

このリポジトリは、Docker Compose で **Ollama LLM サーバー** を立ち上げるテンプレートです。  
`git clone` して `docker compose up -d` するだけで API サーバーが動きます。

## セットアップ手順

```bash
# Clone
git clone https://github.com/yourname/ollama-server.git
cd ollama-server

# 起動
docker compose up -d

# モデルを取得
docker exec -it ollama ollama pull llama3

## GPU を使うための追加手順 (Ubuntu 24.04)

このリポジトリでは `docker-compose.yml` で `gpus: all` を設定しています。ホスト側で NVIDIA ドライバと `nvidia-container-toolkit` を正しくインストールすることで、コンテナから GPU が使えるようになります。以下は最低限の手順です。

1. NVIDIA ドライバをインストールします（GTX 1660 Super に合ったドライバ）。Ubuntu のドライバ管理や `apt` を使います。例:

```bash
# 更新
sudo apt update && sudo apt upgrade -y

# 推奨ドライバの確認とインストール
sudo ubuntu-drivers devices
sudo ubuntu-drivers autoinstall

# 再起動
sudo reboot
```

2. Docker と NVIDIA コンテナツールキットをインストールします。

```bash
# Docker が未インストールの場合は公式手順に従ってインストール
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
	"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
	$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# nvidia-container-toolkit の追加
distribution="$(. /etc/os-release;echo $ID$VERSION_ID)"
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
	sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

3. 動作確認

```bash
# ホストで GPU が見えるか
nvidia-smi

# Docker コンテナから見えるか（テスト用イメージ）
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu24.04 nvidia-smi

# compose で起動している場合は ollama コンテナ内で確認
docker compose up -d
docker exec -it ollama bash -lc "nvidia-smi || echo 'nvidia-smi not available in container'"
```

注意: 一部の古い GPU やドライバでは、Ollama が必要とする CUDA/driver バージョンと合わない場合があります。GTX 1660 Super は比較的新しいカードなので通常は動作しますが、ドライバのバージョンに注意してください。

## トラブルシューティング

- コンテナで `nvidia-smi` が動かない場合は、`sudo systemctl restart docker` を試すか、`nvidia-container-toolkit` のインストール手順を再確認してください。
- Docker が rootless で動いていると GPU が渡せないことがあります。通常は systemd 管理の Docker を使ってください。

### Ollama コンテナ内での確認

Ollama が GPU を使ってモデルをロードしているかを確認するには、コンテナのログやモデルロード時の出力を確認します。

```bash
# ログの確認
docker logs -f ollama

# モデルをダウンロード / 起動している最中に GPU メモリが割り当てられているか確認
docker exec -it ollama bash -lc "watch -n 1 nvidia-smi"

# モデルをプルして起動する例（別ターミナルで実行）
docker exec -it ollama ollama pull llama3
```

もし Ollama が内部で CUDA を利用していれば、`nvidia-smi` の出力にプロセスが表示され、GPU メモリが割り当てられていることが確認できます。


