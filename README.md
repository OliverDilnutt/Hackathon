# Telegram бот на подобие Тамагочи
 
[Бот](https://t.me/tamagochi_turtle_bot)  

 
### **Структура проекта** 
```
.
├── bot.db
├── config.yaml
├── core
│   ├── bot.py
│   ├── database.py
│   ├── engine.py
│   ├── __init__.py
│   ├── interface.py
│   └── utils.py
├── fonts
├── imgs
├── items.yaml
├── messages.yaml
└── start.py
``` 
 
### **Настройка** 
1. Склонируйте этот репозиторий  
``` 
git clone https://github.com/OliverDilnutt/Hackathon.git
``` 
2. Создать виртуальное окружение
```
python3 -m venv .venv
```
3. Загрузить виртуальное окружение  
MacOS/Linux
```
source .venv/bin/activate
```
Windows
```
.venv\Scripts\activate.bat
```
4. Установите все необходимые зависимости, указанные в `requirements.txt` 
``` 
pip install -r requirements.txt 
```
5. Установите переменную окружения  
MacOS/Linux 
```
export TELEGRAM_TOKEN=<TOKEN>
```
6. При необходимости измените `config.yaml` 
7. При необходимости измените `messages.yaml` 
9. Запустите бота с помощью команды  
``` 
python3 start.py 
``` 

 
## Использование 
- /start — запустить бота 
- /debug — получить файл с логами 
 
 
### **Использовано** 
![Python](https://img.shields.io/badge/Python-blue?style=for-the-badge)    
![Telebot](https://img.shields.io/badge/Telebot-lightgray?style=for-the-badge)
