
# Ollama Server

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Nginx](https://img.shields.io/badge/nginx-%23009639.svg?style=for-the-badge&logo=nginx&logoColor=white)](https://nginx.org/)
[![Ollama](https://img.shields.io/badge/Ollama-lightgrey)](https://ollama.com)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![Views](https://komarev.com/ghpvc/?username=sean9061-ollama_server&color=43c6ac&style=flat)

**Ollama Server** は、Docker Compose を利用して、ローカル環境に大規模言語モデル（LLM）の実行環境を迅速に構築するためのプロジェクトです。Nginx をリバースプロキシとして配置し、安全かつ効率的に Ollama API へアクセスできます。さらに、リッチな表示と対話機能を備えたコマンドラインインターフェース（CLI）クライアントも同梱しています。

## 🎨 システム構成図

システムの全体像は（だいたい）以下の通りです。

![System Diagram](docs/ollama_serv_system.drawio.svg)

## ✨ 主な特徴

*   **🚀 簡単なセットアップ**: Docker Compose を使って、コマンド一つでサーバーを起動できます。
*   **🔒 セキュアなアクセス**: Nginx リバースプロキシが Ollama API へのアクセスを中継し、将来的な拡張（認証、SSLなど）も容易です。
*   **🖥️ 高機能なCLIクライアント**:
    *   ストリーミングと非ストリーミングの両モードに対応
    *   Markdown、コードブロックのシンタックスハイライト
    *   会話履歴の管理（`/reset` コマンド）
    *   モデルの動的な切り替え（`/model` コマンド）
    *   思考中アニメーションによる優れたUX
*   **🧩 柔軟なモデル管理**: `ollama/ollama` イメージを利用し、好きなモデルをダウンロードして利用できます。
*   **🎮 GPUサポート**: NVIDIA GPU を活用して、高速な推論を実現します（要 `nvidia-container-toolkit`）。

## 🛠️ 必要なもの

*   [Docker](https://www.docker.com/get-started)
*   [Docker Compose](https://docs.docker.com/compose/install/)
*   [Python 3.9+](https://www.python.org/)
*   (オプション) [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) (GPUを利用する場合)

## 🚀 インストールとセットアップ

1.  **リポジトリをクローンします:**
    ```bash
    git clone https://github.com/sean9061/ollama_server.git
    cd ollama_server
    ```

2.  **Dockerコンテナを起動します:**
    ```bash
    docker-compose up -d
    ```
    サーバーがバックグラウンドで起動します。Ollama API は `http://localhost/api` で利用可能になります。

## 使い方

### Ollama API

Nginx を経由して、ホストマシンのポート `80` が Ollama の API (`http://ollama:11434`) にプロキシされます。
`curl` や他のHTTPクライアントから `http://localhost/api` に対してリクエストを送信できます。

**例: `llama3.2` モデルとの対話**
```bash
curl http://localhost/api/chat -d '{
  "model": "llama3.2",
  "messages": [
    { "role": "user", "content": "Why is the sky blue?" }
  ]
}'
```

### CLIクライアント

よりインタラクティブな体験のために、専用のCLIクライアントを使用できます。

1.  **必要なPythonパッケージをインストールします:**
    ```bash
    pip install -r ollama_cli/requirements.txt
    ```

2.  **CLIクライアントを起動します:**
    ```bash
    python3 ollama_cli/ollama_cli.py --host http://localhost/api --model llama3.2
    ```
    *   `--host`: Ollama APIのエンドポイントを指定します。
    *   `--model`: 使用するモデル名を指定します。

**CLIコマンド:**
*   `/reset`: 現在の会話履歴をリセットします。
*   `/model <model_name>`: 使用するモデルを切り替えます。
*   `/exit`: クライアントを終了します。
*   `/help`: ヘルプメッセージを表示します。

## 🐳 Docker構成

`docker-compose.yml` は2つの主要なサービスを定義しています。

*   **`ollama`**:
    *   `ollama/ollama:latest` イメージを使用します。
    *   モデルデータは `ollama_data` Dockerボリュームに永続化されます。
    *   GPUを利用するために `deploy.resources.reservations` が設定されています。
*   **`nginx`**:
    *   `nginx:alpine` イメージを使用します。
    *   `nginx.conf` をマウントし、リバースプロキシとして機能します。
    *   ポート `80` でリクエストを受け付け、`/api` パスへのリクエストを `ollama` サービスに転送します。

## 今後 気が向いたらやること

- sを付ける（重要）
- Open WebUIの対応
- マルチモーダル化

## 📜 ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。

---

このreadmeはほぼほぼ Gemini 2.5 Pro によって生成されました。