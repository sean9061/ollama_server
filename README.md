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
