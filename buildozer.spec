[app]
# Название приложения
title = LinguaHelp

# Название пакета
package.name = linguahelp

# Домен пакета
package.domain = org.linguahelp

# Путь к main.py в среде Google Colab
source.dir = .

# Расширения файлов,включаемые в сборку
source.include_exts = py,png,jpg,kv,atlas

# Версия приложения
version = 0.1

# Зависимости приложения
requirements = python3,kivy,kivymd==1.2.0,android

# Поддерживаемые ориентации  экрана, индикатор возможности запуска в полноэкранном режиме
orientation = portrait
fullscreen = 0

# Целевой Android API 
android.api = 33

# Минимальный Android API
android.minapi = 21

# Версия Android NDK для использования
android.ndk = 25b
