# Настройка Qwen Code API на VM

Выполните эти команды **на VM** (подключитесь через `ssh root@10.93.26.63`):

## Шаг 1: Установка Qwen Code CLI

```bash
# Установите pnpm (если ещё не установлен)
curl -fsSL https://get.pnpm.io/install.sh | sh -

# Перезагрузите оболочку или выполните:
source ~/.bashrc

# Установите Qwen Code CLI глобально
pnpm add -g @qwen-code/qwen-code
```

## Шаг 2: Аутентификация

```bash
# Запустите Qwen Code
qwen

# В чате напишите: /auth
# Откройте ссылку в браузере и войдите через GitHub
# После успешного входа нажмите /quit для выхода
```

## Шаг 3: Проверка ключа API

```bash
# Проверьте, что файл с ключами существует
cat ~/.qwen/oauth_creds.json | jq .

# Если файл существует и не пустой, ключ получен успешно
```

## Шаг 4: Настройка qwen-code-oai-proxy

```bash
# Склонируйте репозиторий
cd ~
git clone https://github.com/inno-se-toolkit/qwen-code-oai-proxy ~/qwen-code-oai-proxy
cd ~/qwen-code-oai-proxy

# Создайте .env файл
cp .env.example .env

# Получите API ключ из oauth_creds.json
API_KEY=$(cat ~/.qwen/oauth_creds.json | jq -r '.api_key')

# Вставьте ключ в .env автоматически
sed -i "s/QWEN_API_KEY=.*/QWEN_API_KEY=$API_KEY/" .env

# Проверьте, что ключ установлен
cat .env | grep QWEN_API_KEY
```

## Шаг 5: Запуск сервера

```bash
# Запустите через Docker
docker compose up --build -d

# Проверьте, что контейнер запущен
docker ps | grep qwen

# Проверьте порт (должен быть 42005)
cat .env | grep HOST_PORT
```

## Шаг 6: Тестирование API

```bash
# Получите порт и ключ
PORT=$(cat .env | grep HOST_PORT | cut -d'=' -f2)
KEY=$(cat .env | grep QWEN_API_KEY | cut -d'=' -f2)

# Протестируйте API
curl -s http://127.0.0.1:$PORT/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $KEY" \
  -d '{"model":"qwen3-coder-plus","messages":[{"role":"user","content":"What is 2+2?"}]}' | jq .
```

Если вы получили ответ вида:
```json
{
  "choices": [{"message": {"content": "2 + 2 = 4"}}]
}
```

— сервер работает!

## Шаг 7: Откройте порт для внешнего доступа

```bash
# Разрешите подключение к порту 42005
ufw allow 42005/tcp

# Проверьте правила
ufw status
```

## Шаг 8: Проверка с локальной машины

Теперь с **Mac** выполните:

```bash
curl -s http://10.93.26.63:42005/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ваш-ключ>" \
  -d '{"model":"qwen3-coder-plus","messages":[{"role":"user","content":"test"}]}' | python3 -m json.tool
```

Если ответ получен — настройка завершена!
