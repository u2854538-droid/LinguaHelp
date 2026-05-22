import sqlite3
from datetime import datetime, timedelta, date
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton, MDFillRoundFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.toast import toast
from kivymd.uix.dialog import MDDialog
from kivymd.uix.progressbar import MDProgressBar


INITIAL_WORDS = [
    ("apple", "яблоко", "I eat an apple every day", "en", "easy"),
    ("car", "машина", "My car is red", "en", "easy"),
    ("house", "дом", "This is my house", "en", "easy"),
    ("dog", "собака", "The dog is barking", "en", "medium"),
    ("cat", "кошка", "The cat sleeps on the sofa", "en", "medium"),
    ("beautiful", "красивый", "She is beautiful", "en", "hard"),
    ("quickly", "быстро", "He runs quickly", "en", "hard"),
    ("hola", "привет", "Hola, ¿cómo estás?", "es", "easy"),
    ("gracias", "спасибо", "Muchas gracias por tu ayuda", "es", "easy"),
    ("casa", "дом", "Mi casa es tu casa", "es", "medium"),
    ("perro", "собака", "El perro ladra", "es", "medium"),
    ("bonita", "красивая", "La flor es bonita", "es", "hard"),
    ("hallo", "привет", "Hallo, wie geht es dir?", "de", "easy"),
    ("danke", "спасибо", "Danke für deine Hilfe", "de", "easy"),
    ("haus", "дом", "Das Haus ist groß", "de", "medium"),
    ("hund", "собака", "Der Hund bellt", "de", "medium"),
    ("schön", "красивый", "Das Wetter ist schön", "de", "hard"),
]

SKY_MID = [0.70, 0.82, 0.96, 1]
CORNFLOWER = [0.55, 0.65, 0.90, 1]
CORNFLOWER_DARK = [0.45, 0.55, 0.82, 1]
CORNFLOWER_LIGHT = [0.70, 0.78, 0.95, 1]
WHITE = [1, 1, 1, 1]
SUCCESS = [0.55, 0.80, 0.70, 1]
ERROR = [0.85, 0.60, 0.70, 1]
TEXT_LIGHT = [0.45, 0.50, 0.65, 1]
SKY_LIGHT = [0.92, 0.96, 0.99, 1]


class Database:
    def __init__(self, db_name='linguahelp.db'):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()
        self.seed_data()

    def create_tables(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                translation TEXT NOT NULL,
                example TEXT,
                language TEXT DEFAULT 'en',
                difficulty TEXT DEFAULT 'easy',
                interval INTEGER DEFAULT 0,
                ease_factor REAL DEFAULT 2.5,
                repetitions INTEGER DEFAULT 0,
                next_review TEXT,
                level INTEGER DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                streak INTEGER DEFAULT 0,
                total_reviewed INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                last_review_date TEXT
            )
        ''')
        c.execute("INSERT OR IGNORE INTO stats (id) VALUES (1)")
        self.conn.commit()

    def seed_data(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM words")
        if c.fetchone()[0] == 0:
            today = date.today().isoformat()
            for w in INITIAL_WORDS:
                c.execute(
                    "INSERT INTO words (word, translation, example, language, difficulty, next_review) VALUES (?, ?, ?, ?, ?, ?)",
                    (w[0], w[1], w[2], w[3], w[4], today)
                )
            self.conn.commit()

    def get_due_words(self, language, difficulty, limit=20):
        today = date.today().isoformat()
        c = self.conn.cursor()
        c.execute(
            "SELECT id, word, translation, example, interval, ease_factor, repetitions, level "
            "FROM words WHERE next_review <= ? AND language = ? AND difficulty = ? "
            "ORDER BY level ASC LIMIT ?",
            (today, language, difficulty, limit)
        )
        return c.fetchall()

    def get_all_words(self, language=None):
        c = self.conn.cursor()
        if language:
            c.execute(
                "SELECT id, word, translation, example, level, language FROM words WHERE language = ? ORDER BY id DESC",
                (language,))
        else:
            c.execute("SELECT id, word, translation, example, level, language FROM words ORDER BY id DESC")
        return c.fetchall()

    def add_word(self, word, translation, example, language, difficulty):
        c = self.conn.cursor()
        today = date.today().isoformat()
        c.execute(
            "INSERT INTO words (word, translation, example, language, difficulty, next_review) VALUES (?, ?, ?, ?, ?, ?)",
            (word, translation, example, language, difficulty, today)
        )
        self.conn.commit()
        return True

    def delete_word(self, word_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM words WHERE id=?", (word_id,))
        self.conn.commit()
        return True

    def update_word_progress(self, word_id, rating, interval, ease, reps, is_correct):
        new_date = (date.today() + timedelta(days=interval)).isoformat()
        c = self.conn.cursor()
        c.execute("SELECT level FROM words WHERE id=?", (word_id,))
        result = c.fetchone()
        level = result[0] if result else 0
        if is_correct and level < 5:
            level += 1
        elif not is_correct and level > 0:
            level -= 1
        c.execute(
            "UPDATE words SET interval=?, ease_factor=?, repetitions=?, next_review=?, level=? WHERE id=?",
            (interval, ease, reps, new_date, level, word_id)
        )
        self.conn.commit()

    def update_stats(self, is_correct):
        today = date.today().isoformat()
        c = self.conn.cursor()
        c.execute("SELECT streak, total_reviewed, correct_count, last_review_date FROM stats WHERE id=1")
        row = c.fetchone()
        if not row:
            return
        streak, total, correct = row[0], row[1] + 1, row[2] + (1 if is_correct else 0)
        if row[3] != today:
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            streak = streak + 1 if row[3] == yesterday else 1
        c.execute(
            "UPDATE stats SET streak=?, total_reviewed=?, correct_count=?, last_review_date=? WHERE id=1",
            (streak, total, correct, today)
        )
        self.conn.commit()

    def get_stats(self):
        c = self.conn.cursor()
        c.execute("SELECT streak, total_reviewed, correct_count FROM stats WHERE id=1")
        row = c.fetchone()
        if not row:
            return 0, 0, 0, 0
        streak, total, correct = row
        acc = (correct / total * 100) if total > 0 else 0
        return streak, total, correct, acc

    def reset_progress(self):
        c = self.conn.cursor()
        today = date.today().isoformat()
        c.execute("UPDATE stats SET streak=0, total_reviewed=0, correct_count=0, last_review_date=NULL WHERE id=1")
        c.execute("UPDATE words SET interval=0, ease_factor=2.5, repetitions=0, level=0, next_review=?", (today,))
        self.conn.commit()

    def close(self):
        self.conn.close()


class SRSEngine:
    @staticmethod
    def calculate_next_interval(ease_factor, rating, interval, repetitions):
        if rating < 3:
            return 1, max(1.3, ease_factor - 0.2), 0
        new_reps = repetitions + 1
        if new_reps == 1:
            interval = 1
        elif new_reps == 2:
            interval = 6
        else:
            interval = int(interval * ease_factor)
        new_ease = ease_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
        return interval, max(1.3, new_ease), new_reps


class LearningCard(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.92, None)
        self.height = dp(320)
        self.pos_hint = {"center_x": 0.5, "center_y": 0.55}
        self.elevation = 4
        self.radius = [dp(20)]
        self.md_bg_color = WHITE
        self.padding = [dp(20), dp(20), dp(20), dp(20)]
        self.orientation = "vertical"
        self.spacing = dp(12)

        self.word_label = MDLabel(
            font_style="H4",
            halign="center",
            bold=True,
            size_hint=(1, None),
            height=dp(60),
            theme_text_color="Primary"
        )

        self.trans_label = MDLabel(
            font_style="H5",
            halign="center",
            theme_text_color="Secondary",
            size_hint=(1, None),
            height=dp(50),
        )

        self.sep = Widget(size_hint=(1, None), height=dp(1))
        with self.sep.canvas:
            Color(*CORNFLOWER_LIGHT)
            self.sep_rect = Rectangle(pos=self.sep.pos, size=self.sep.size)
        self.sep.bind(pos=self.update_sep, size=self.update_sep)

        self.example_label = MDLabel(
            font_style="Body1",
            italic=True,
            theme_text_color="Hint",
            halign="center",
            valign="top",
            size_hint=(1, None),
            height=dp(70),
        )
        self.bind(size=self._update_example_text_size)

        self.btn_layout = BoxLayout(
            spacing=dp(12),
            size_hint=(1, None),
            height=dp(52),
        )

        self.btn_bad = MDFillRoundFlatButton(
            text="Не знаю",
            md_bg_color=ERROR,
            size_hint=(0.48, 1),
            font_size=sp(14),
        )
        self.btn_good = MDFillRoundFlatButton(
            text="Знаю",
            md_bg_color=SUCCESS,
            size_hint=(0.48, 1),
            font_size=sp(14),
        )

        self.btn_bad.bind(on_release=lambda x: self.on_answer(2))
        self.btn_good.bind(on_release=lambda x: self.on_answer(4))

        self.btn_layout.add_widget(self.btn_bad)
        self.btn_layout.add_widget(self.btn_good)

        self.add_widget(self.word_label)
        self.add_widget(self.trans_label)
        self.add_widget(self.sep)
        self.add_widget(self.example_label)
        self.add_widget(Widget(size_hint_y=1)) 
        self.add_widget(self.btn_layout)

        self.current_trans = ""

    def _update_example_text_size(self, instance, value):
        self.example_label.text_size = (value[0] - dp(20), None)

    def update_sep(self, instance, value):
        if hasattr(self, 'sep_rect'):
            self.sep_rect.pos = instance.pos
            self.sep_rect.size = instance.size

    def set_word(self, word, translation, example):
        self.word_label.text = word
        self.trans_label.text = "?"
        self.example_label.text = f"Пример: {example}" if example else ""
        self.current_trans = translation

    def show_answer(self):
        self.trans_label.text = self.current_trans

    def on_answer(self, rating):
        app = MDApp.get_running_app()
        app.on_answer(rating)


class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.circles = []
        self.setup_ui()
        Clock.schedule_once(self.create_animated_circles, 0.1)

    def setup_ui(self):
        self.main_layout = FloatLayout()
        with self.main_layout.canvas.before:
            Color(*SKY_LIGHT)
            self.rect = Rectangle(pos=self.main_layout.pos, size=self.main_layout.size)
        self.main_layout.bind(pos=self.update_rect, size=self.update_rect)

        self.logo_card = MDCard(
            size_hint=(0.85, None),
            height=dp(280),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            radius=[dp(25)],
            md_bg_color=[1, 1, 1, 0.85]
        )

        logo_layout = BoxLayout(
            orientation='vertical',
            padding=[dp(24), dp(24), dp(24), dp(24)],
            spacing=dp(16)
        )

        logo_layout.add_widget(
            MDLabel(
                text="LinguaHelp",
                font_style="H3",
                halign="center",
                bold=True,
                color=CORNFLOWER_DARK,
                size_hint=(1, None),
                height=dp(55),
            )
        )

        subtitle = MDLabel(
            text="Учи слова эффективно\nинтервальным повторением",
            halign="center",
            color=TEXT_LIGHT,
            size_hint=(1, None),
            height=dp(60),
        )
        subtitle.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
        logo_layout.add_widget(subtitle)

        logo_layout.add_widget(Widget(size_hint=(1, None), height=dp(8)))

        start_btn = MDRaisedButton(
            text="Начать",
            size_hint=(0.65, None),
            height=dp(48),
            pos_hint={'center_x': 0.5},
            md_bg_color=CORNFLOWER,
            font_size=sp(16),
            on_release=self.start_app
        )
        logo_layout.add_widget(start_btn)

        self.logo_card.add_widget(logo_layout)
        self.main_layout.add_widget(self.logo_card)

        self.logo_card.opacity = 0
        Animation(opacity=1, duration=0.8, t='out_back').start(self.logo_card)
        self.add_widget(self.main_layout)

    def create_animated_circles(self, dt):
        w, h = Window.width, Window.height
        circles_data = [
            (0.1, 0.8, dp(120), CORNFLOWER_LIGHT, 0.3),
            (0.9, 0.9, dp(90), CORNFLOWER_LIGHT, 0.25),
            (0.85, 0.15, dp(100), CORNFLOWER, 0.15),
            (0.2, 0.2, dp(70), SKY_MID, 0.4),
            (0.7, 0.5, dp(80), SKY_MID, 0.25),
        ]
        for rx, ry, size, color, alpha in circles_data:
            with self.main_layout.canvas.before:
                Color(color[0], color[1], color[2], alpha)
                circle = Ellipse(
                    pos=(w * rx - size / 2, h * ry - size / 2),
                    size=(size, size)
                )
            self.circles.append(circle)
            anim = (
                Animation(size=(size * 1.2, size * 1.2), duration=2.5) +
                Animation(size=(size, size), duration=2.5)
            )
            anim.repeat = True
            anim.start(circle)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def start_app(self, instance):
        Animation(opacity=0, duration=0.4).start(self.logo_card)
        Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'main'), 0.5)


class LearningScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*SKY_LIGHT)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

        layout = FloatLayout()

        self.status_label = MDLabel(
            text="Выберите фильтры в настройках",
            halign="center",
            theme_text_color="Secondary",
            size_hint=(1, None),
            height=dp(36),
            font_size=sp(13),
            pos_hint={'center_x': 0.5, 'y': 0.02}
        )

        self.card = LearningCard()

        self.restart_btn = MDRaisedButton(
            text="Начать заново",
            md_bg_color=CORNFLOWER,
            size_hint=(0.6, None),
            height=dp(48),
            pos_hint={'center_x': 0.5, 'center_y': 0.15},
            on_release=self.restart_lesson
        )
        self.restart_btn.opacity = 0
        self.restart_btn.disabled = True

        layout.add_widget(self.card)
        layout.add_widget(self.status_label)
        layout.add_widget(self.restart_btn)
        self.add_widget(layout)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def restart_lesson(self, instance):
        MDApp.get_running_app().restart_lesson()

    def show_restart_button(self, show):
        self.restart_btn.opacity = 1 if show else 0
        self.restart_btn.disabled = not show


class StatsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setup_ui()

    def setup_ui(self):
        with self.canvas.before:
            Color(*SKY_LIGHT)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

        root = BoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(16), dp(16), dp(16)],
            spacing=dp(14),
        )

        title = MDLabel(
            text="Ваша статистика",
            font_style="H5",
            halign="center",
            size_hint=(1, None),
            height=dp(44),
            color=CORNFLOWER_DARK
        )
        root.add_widget(title)

        streak_card = self._make_stat_card("Серия дней")
        self.streak_lbl = MDLabel(
            text="0", font_style="H3", halign="center",
            color=CORNFLOWER, size_hint=(1, None), height=dp(48), bold=True
        )
        streak_card.add_widget(self.streak_lbl)
        root.add_widget(streak_card)

        reviewed_card = self._make_stat_card("Пройдено всего")
        self.reviewed_lbl = MDLabel(
            text="0", font_style="H3", halign="center",
            color=CORNFLOWER, size_hint=(1, None), height=dp(48), bold=True
        )
        reviewed_card.add_widget(self.reviewed_lbl)
        root.add_widget(reviewed_card)

        acc_card = self._make_stat_card("Точность ответов")
        self.acc_bar = MDProgressBar(
            value=0, size_hint=(1, None), height=dp(12), color=CORNFLOWER
        )
        self.acc_lbl = MDLabel(
            text="0%", font_style="H4", halign="center",
            color=CORNFLOWER, size_hint=(1, None), height=dp(42), bold=True
        )
        acc_card.add_widget(self.acc_bar)
        acc_card.add_widget(self.acc_lbl)
        root.add_widget(acc_card)

        root.add_widget(Widget())

        self.add_widget(root)

    def _make_stat_card(self, title_text):
        card = MDCard(
            size_hint=(1, None),
            height=dp(108),
            radius=[dp(18)],
            md_bg_color=[1, 1, 1, 0.95],
            elevation=2,
            padding=[dp(16), dp(10), dp(16), dp(10)],
            orientation='vertical',
            spacing=dp(6)
        )
        card.add_widget(MDLabel(
            text=title_text,
            font_style="Subtitle1",
            halign="center",
            color=TEXT_LIGHT,
            size_hint=(1, None),
            height=dp(26)
        ))
        return card

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size


class DictionaryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_language = "en"
        self.setup_ui()

    def setup_ui(self):
        with self.canvas.before:
            Color(*SKY_LIGHT)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

        root = BoxLayout(orientation='vertical')

        top = BoxLayout(
            orientation='vertical',
            size_hint=(1, None),
            padding=[dp(12), dp(10), dp(12), dp(6)],
            spacing=dp(8),
        )
        top.bind(minimum_height=top.setter('height'))

        title = MDLabel(
            text="Мой словарь",
            font_style="H5",
            halign="center",
            size_hint=(1, None),
            height=dp(40)
        )
        top.add_widget(title)

        add_card = MDCard(
            size_hint=(1, None),
            radius=[dp(18)],
            md_bg_color=WHITE,
            elevation=2,
            padding=[dp(14), dp(10), dp(14), dp(10)],
        )
        add_inner = BoxLayout(
            orientation='vertical',
            spacing=dp(6),
            size_hint_y=None,
        )
        add_inner.bind(minimum_height=add_inner.setter('height'))
        add_card.bind(minimum_height=add_card.setter('height'))

        add_inner.add_widget(MDLabel(
            text="Добавить новое слово",
            font_style="Subtitle1",
            size_hint=(1, None),
            height=dp(28)
        ))

        self.new_word_input = MDTextField(
            hint_text="Слово",
            mode="rectangle",
            size_hint=(1, None),
            height=dp(48),
            font_size=sp(14),
        )
        self.new_trans_input = MDTextField(
            hint_text="Перевод",
            mode="rectangle",
            size_hint=(1, None),
            height=dp(48),
            font_size=sp(14),
        )
        self.new_example_input = MDTextField(
            hint_text="Пример",
            mode="rectangle",
            size_hint=(1, None),
            height=dp(48),
            font_size=sp(14),
        )
        add_btn = MDRaisedButton(
            text="Добавить",
            md_bg_color=CORNFLOWER,
            size_hint=(0.55, None),
            pos_hint={'center_x': 0.5},
            height=dp(44),
            on_release=self.add_new_word
        )

        add_inner.add_widget(self.new_word_input)
        add_inner.add_widget(self.new_trans_input)
        add_inner.add_widget(self.new_example_input)
        add_inner.add_widget(add_btn)
        add_card.add_widget(add_inner)
        top.add_widget(add_card)


        filter_layout = BoxLayout(size_hint=(1, None), height=dp(46), spacing=dp(10))
        filter_layout.add_widget(MDLabel(
            text="Показать:",
            size_hint=(0.32, 1),
            font_size=sp(13),
            valign='middle',
            halign='left'
        ))
        self.lang_filter_btn = MDRaisedButton(
            text="Английский",
            md_bg_color=CORNFLOWER,
            size_hint=(0.68, None),
            height=dp(40),
            font_size=sp(13),
            on_release=self.change_language_filter
        )
        filter_layout.add_widget(self.lang_filter_btn)
        top.add_widget(filter_layout)

        root.add_widget(top)
        self.words_list = ScrollView(size_hint=(1, 1))
        self.words_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(6),
            padding=[dp(12), dp(4), dp(12), dp(8)]
        )
        self.words_container.bind(minimum_height=self.words_container.setter('height'))
        self.words_list.add_widget(self.words_container)
        root.add_widget(self.words_list)

        self.add_widget(root)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def change_language_filter(self, instance):
        if self.current_language == "en":
            self.current_language = "es"
            self.lang_filter_btn.text = "Испанский"
            self.lang_filter_btn.md_bg_color = CORNFLOWER_LIGHT
        elif self.current_language == "es":
            self.current_language = "de"
            self.lang_filter_btn.text = "Немецкий"
            self.lang_filter_btn.md_bg_color = CORNFLOWER_LIGHT
        else:
            self.current_language = "en"
            self.lang_filter_btn.text = "Английский"
            self.lang_filter_btn.md_bg_color = CORNFLOWER
        self.load_words()

    def load_words(self):
        app = MDApp.get_running_app()
        words = app.db.get_all_words(self.current_language)
        self.words_container.clear_widgets()
        if not words:
            self.words_container.add_widget(MDLabel(
                text="Словарь пуст. Добавьте новые слова!",
                halign="center",
                theme_text_color="Secondary",
                size_hint=(1, None),
                height=dp(50)
            ))
            return

        for wid, word, trans, example, level, lang in words:
            card = MDCard(
                size_hint=(1, None),
                height=dp(74),
                radius=[dp(14)],
                md_bg_color=WHITE,
                elevation=1,
                padding=[dp(12), dp(8), dp(4), dp(8)]
            )
            card_layout = BoxLayout(orientation='horizontal', spacing=dp(8))

            left_layout = BoxLayout(orientation='vertical', size_hint_x=0.65, spacing=dp(2))
            word_label = MDLabel(
                text=word,
                font_style="Subtitle1",
                bold=True,
                size_hint=(1, None),
                height=dp(28),
                halign="left",
                shorten=True,
                shorten_from='right'
            )
            word_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))

            trans_label = MDLabel(
                text=trans,
                theme_text_color="Secondary",
                font_size=sp(13),
                size_hint=(1, None),
                height=dp(22),
                halign="left",
                shorten=True,
                shorten_from='right'
            )
            trans_label.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))

            left_layout.add_widget(word_label)
            left_layout.add_widget(trans_label)

            right_layout = BoxLayout(orientation='horizontal', size_hint_x=0.35, spacing=dp(2))
            circles = "●" * level + "○" * (5 - level)
            level_label = MDLabel(
                text=circles,
                halign='right',
                color=CORNFLOWER,
                size_hint=(0.6, 1),
                font_size=sp(12),
                valign='middle'
            )
            delete_btn = MDIconButton(
                icon="delete",
                theme_text_color="Hint",
                size_hint=(0.4, 1),
            )
            delete_btn.word_id = wid
            delete_btn.bind(on_release=lambda x: self.delete_word(x.word_id))

            right_layout.add_widget(level_label)
            right_layout.add_widget(delete_btn)

            card_layout.add_widget(left_layout)
            card_layout.add_widget(right_layout)
            card.add_widget(card_layout)
            self.words_container.add_widget(card)

    def delete_word(self, word_id):
        def confirm(instance):
            app = MDApp.get_running_app()
            app.db.delete_word(word_id)
            self.load_words()
            app.load_next_word()
            app.update_stats_ui()
            toast("Слово удалено")
            dialog.dismiss()

        dialog = MDDialog(
            title="Удалить слово?",
            text="Это действие нельзя отменить.",
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda x: dialog.dismiss()),
                MDRaisedButton(text="Удалить", md_bg_color=ERROR, on_release=confirm)
            ]
        )
        dialog.open()

    def add_new_word(self, instance):
        word = self.new_word_input.text.strip()
        trans = self.new_trans_input.text.strip()
        example = self.new_example_input.text.strip()
        if not word or not trans:
            toast("Заполните слово и перевод")
            return
        app = MDApp.get_running_app()
        app.db.add_word(word, trans, example, self.current_language, "easy")
        toast("Слово добавлено!")
        self.new_word_input.text = ""
        self.new_trans_input.text = ""
        self.new_example_input.text = ""
        self.load_words()
        app.load_next_word()
        app.update_stats_ui()


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*SKY_LIGHT)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

        scroll = ScrollView()
        layout = BoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(16), dp(16), dp(16)],
            spacing=dp(18),
            size_hint_y=None,
        )
        layout.bind(minimum_height=layout.setter('height'))

        title = MDLabel(
            text="Настройки обучения",
            font_style="H5",
            size_hint=(1, None),
            height=dp(44)
        )

        lang_card = MDCard(
            size_hint=(1, None),
            height=dp(130),
            radius=[dp(18)],
            md_bg_color=WHITE,
            elevation=2,
            padding=[dp(16), dp(14), dp(16), dp(14)],
            orientation='vertical',
            spacing=dp(10)
        )
        lang_card.add_widget(MDLabel(
            text="Язык", font_style="Subtitle1",
            size_hint=(1, None), height=dp(26)
        ))
        lang_buttons = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(46))
        self.en_btn = MDRaisedButton(text="Английский", md_bg_color=CORNFLOWER, size_hint=(0.33, 1), font_size=sp(12))
        self.es_btn = MDRaisedButton(text="Испанский", md_bg_color=CORNFLOWER_LIGHT, size_hint=(0.33, 1), font_size=sp(12))
        self.de_btn = MDRaisedButton(text="Немецкий", md_bg_color=CORNFLOWER_LIGHT, size_hint=(0.33, 1), font_size=sp(12))
        self.en_btn.bind(on_release=lambda x: self.set_language("en"))
        self.es_btn.bind(on_release=lambda x: self.set_language("es"))
        self.de_btn.bind(on_release=lambda x: self.set_language("de"))
        lang_buttons.add_widget(self.en_btn)
        lang_buttons.add_widget(self.es_btn)
        lang_buttons.add_widget(self.de_btn)
        lang_card.add_widget(lang_buttons)

        diff_card = MDCard(
            size_hint=(1, None),
            height=dp(130),
            radius=[dp(18)],
            md_bg_color=WHITE,
            elevation=2,
            padding=[dp(16), dp(14), dp(16), dp(14)],
            orientation='vertical',
            spacing=dp(10)
        )
        diff_card.add_widget(MDLabel(
            text="Уровень сложности", font_style="Subtitle1",
            size_hint=(1, None), height=dp(26)
        ))
        diff_buttons = BoxLayout(spacing=dp(8), size_hint=(1, None), height=dp(46))
        self.easy_btn = MDRaisedButton(text="Лёгкий", md_bg_color=CORNFLOWER, size_hint=(0.33, 1), font_size=sp(12))
        self.medium_btn = MDRaisedButton(text="Средний", md_bg_color=CORNFLOWER_LIGHT, size_hint=(0.33, 1), font_size=sp(12))
        self.hard_btn = MDRaisedButton(text="Сложный", md_bg_color=CORNFLOWER_LIGHT, size_hint=(0.33, 1), font_size=sp(12))
        self.easy_btn.bind(on_release=lambda x: self.set_difficulty("easy"))
        self.medium_btn.bind(on_release=lambda x: self.set_difficulty("medium"))
        self.hard_btn.bind(on_release=lambda x: self.set_difficulty("hard"))
        diff_buttons.add_widget(self.easy_btn)
        diff_buttons.add_widget(self.medium_btn)
        diff_buttons.add_widget(self.hard_btn)
        diff_card.add_widget(diff_buttons)

        reset_btn = MDRaisedButton(
            text="Сбросить прогресс",
            md_bg_color=ERROR,
            size_hint=(0.7, None),
            height=dp(50),
            pos_hint={'center_x': 0.5},
            on_release=self.reset_progress
        )

        layout.add_widget(title)
        layout.add_widget(lang_card)
        layout.add_widget(diff_card)
        layout.add_widget(reset_btn)

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def set_language(self, lang):
        app = MDApp.get_running_app()
        app.set_language(lang)
        self.update_buttons(lang, app.difficulty)

    def set_difficulty(self, diff):
        app = MDApp.get_running_app()
        app.set_difficulty(diff)
        self.update_buttons(app.language, diff)

    def update_buttons(self, lang, diff):
        for btn, l in [(self.en_btn, "en"), (self.es_btn, "es"), (self.de_btn, "de")]:
            btn.md_bg_color = CORNFLOWER if lang == l else CORNFLOWER_LIGHT
        for btn, d in [(self.easy_btn, "easy"), (self.medium_btn, "medium"), (self.hard_btn, "hard")]:
            btn.md_bg_color = CORNFLOWER if diff == d else CORNFLOWER_LIGHT

    def reset_progress(self, instance):
        MDApp.get_running_app().reset_progress()
        toast("Прогресс сброшен")

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*SKY_LIGHT)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

        layout = BoxLayout(orientation='vertical')

        toolbar = MDTopAppBar(
            title="LinguaHelp",
            md_bg_color=CORNFLOWER,
            specific_text_color=WHITE,
            elevation=0,
        )
        layout.add_widget(toolbar)

        self.sm = ScreenManager(size_hint_y=1)
        self.learn_screen = LearningScreen(name='learn')
        self.stats_screen = StatsScreen(name='stats')
        self.dictionary_screen = DictionaryScreen(name='dictionary')
        self.settings_screen = SettingsScreen(name='settings')
        self.sm.add_widget(self.learn_screen)
        self.sm.add_widget(self.stats_screen)
        self.sm.add_widget(self.dictionary_screen)
        self.sm.add_widget(self.settings_screen)
        layout.add_widget(self.sm)

        bottom_nav = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(72),
            padding=[dp(6), dp(6), dp(6), dp(6)],
            spacing=dp(6)
        )
        with bottom_nav.canvas.before:
            Color(*CORNFLOWER)
            self.nav_rect = Rectangle(pos=bottom_nav.pos, size=bottom_nav.size)
        bottom_nav.bind(pos=self.update_nav_rect, size=self.update_nav_rect)

        nav_items = [
            ('learn', 'book-open-page-variant', 'Учёба'),
            ('dictionary', 'book-open-variant', 'Словарь'),
            ('stats', 'chart-bar', 'Стат.'),
            ('settings', 'cog', 'Настройки'),
        ]

        self.nav_btns = {}
        for name, icon, label_text in nav_items:
            btn = MDCard(
                radius=[dp(12)],
                md_bg_color=CORNFLOWER_LIGHT if name == 'learn' else CORNFLOWER,
                size_hint=(0.25, 1),
            )
            btn.name = name
            btn.bind(on_release=lambda x, n=name: self.switch_to(n))

            btn_inner = BoxLayout(
                orientation='vertical',
                padding=[dp(4), dp(4), dp(4), dp(4)],
                spacing=dp(2)
            )
            icon_color = CORNFLOWER_DARK if name == 'learn' else WHITE
            icon_widget = MDIconButton(
                icon=icon,
                theme_text_color="Custom",
                text_color=icon_color,
                size_hint=(1, 0.6),
                icon_size=sp(22),
            )
            lbl = MDLabel(
                text=label_text,
                theme_text_color="Custom",
                text_color=icon_color,
                halign="center",
                font_size=sp(10),
                size_hint=(1, None),
                height=dp(16),
            )
            btn_inner.add_widget(icon_widget)
            btn_inner.add_widget(lbl)
            btn.add_widget(btn_inner)
            bottom_nav.add_widget(btn)
            self.nav_btns[name] = (btn, icon_widget, lbl)

        layout.add_widget(bottom_nav)
        self.add_widget(layout)

    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def update_nav_rect(self, instance, value):
        self.nav_rect.pos = instance.pos
        self.nav_rect.size = instance.size

    def switch_to(self, screen_name):
        self.sm.current = screen_name
        for name, (btn, icon_w, lbl) in self.nav_btns.items():
            active = (name == screen_name)
            btn.md_bg_color = CORNFLOWER_LIGHT if active else CORNFLOWER
            color = CORNFLOWER_DARK if active else WHITE
            icon_w.text_color = color
            lbl.color = color


class LinguaHelpApp(MDApp):
    language = "en"
    difficulty = "easy"
    current_word_id = None
    current_translation = None
    current_example = None
    current_interval = None
    current_ease = None
    current_reps = None
    learning_words = []
    current_index = 0

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.db = Database()
        self.sm = ScreenManager()
        self.splash = SplashScreen(name='splash')
        self.main = MainScreen(name='main')
        self.sm.add_widget(self.splash)
        self.sm.add_widget(self.main)
        return self.sm

    def on_start(self):
        Clock.schedule_once(self.init_app, 0.5)

    def init_app(self, dt):
        self.update_stats_ui()
        self.load_next_word()

    def load_next_word(self, *args):
        if not hasattr(self.main, 'learn_screen'):
            Clock.schedule_once(self.load_next_word, 0.1)
            return
        words = self.db.get_due_words(self.language, self.difficulty, limit=20)
        self.learning_words = words
        self.current_index = 0
        self.main.learn_screen.show_restart_button(False)
        self.show_current_word()

    def restart_lesson(self):
        self.current_index = 0
        self.main.learn_screen.show_restart_button(False)
        self.show_current_word()
        self.main.learn_screen.status_label.text = "Урок начат заново!"

    def show_current_word(self):
        if not hasattr(self.main, 'learn_screen'):
            return
        card = self.main.learn_screen.card
        if self.current_index < len(self.learning_words):
            wid, w, t, e, interval, ease, reps, level = self.learning_words[self.current_index]
            self.current_word_id = wid
            self.current_translation = t
            self.current_example = e
            self.current_interval = interval
            self.current_ease = ease
            self.current_reps = reps
            card.set_word(w, t, e)
            self.main.learn_screen.status_label.text = (
                f"Слово {self.current_index + 1} из {len(self.learning_words)}"
            )
            card.opacity = 0
            Animation(opacity=1, duration=0.35, t='out_quad').start(card)
        else:
            card.word_label.text = "Урок завершён!"
            card.trans_label.text = ""
            card.example_label.text = f"Вы повторили {len(self.learning_words)} слов"
            self.main.learn_screen.status_label.text = "Хотите повторить?"
            self.main.learn_screen.show_restart_button(True)

    def on_answer(self, rating):
        if self.current_word_id is None:
            return
        is_correct = rating >= 3
        new_interval, new_ease, new_reps = SRSEngine.calculate_next_interval(
            self.current_ease, rating, self.current_interval, self.current_reps
        )
        self.db.update_word_progress(
            self.current_word_id, rating, new_interval, new_ease, new_reps, is_correct
        )
        self.db.update_stats(is_correct)
        toast("Правильно! \u2713" if is_correct else f"Неправильно. Ответ: {self.current_translation}")
        self.current_index += 1
        self.update_stats_ui()
        Clock.schedule_once(lambda dt: self.show_current_word(), 0.3)

    def update_stats_ui(self, *args):
        if not hasattr(self, 'main') or not hasattr(self.main, 'stats_screen'):
            Clock.schedule_once(self.update_stats_ui, 0.1)
            return
        streak, total, correct, acc = self.db.get_stats()
        self.main.stats_screen.streak_lbl.text = str(streak)
        self.main.stats_screen.reviewed_lbl.text = str(total)
        self.main.stats_screen.acc_bar.value = acc
        self.main.stats_screen.acc_lbl.text = f"{acc:.1f}%"

    def set_language(self, lang):
        self.language = lang
        self.load_next_word()
        self.update_stats_ui()
        if hasattr(self.main, 'dictionary_screen'):
            ds = self.main.dictionary_screen
            ds.current_language = lang
            lang_names = {"en": "Английский", "es": "Испанский", "de": "Немецкий"}
            ds.lang_filter_btn.text = lang_names.get(lang, "Английский")
            ds.lang_filter_btn.md_bg_color = CORNFLOWER if lang == "en" else CORNFLOWER_LIGHT
            ds.load_words()

    def set_difficulty(self, diff):
        self.difficulty = diff
        self.load_next_word()
        self.update_stats_ui()

    def reset_progress(self):
        self.db.reset_progress()
        self.load_next_word()
        self.update_stats_ui()

    def on_stop(self):
        self.db.close()


if __name__ == '__main__':
    LinguaHelpApp().run()
