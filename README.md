# 🎥 Film Roulette

**Film Roulette** is a command-line tool that randomly selects a film from around the world using live Wikipedia categories. It's designed to help you discover great foreign and domestic films based on country, genre, and optional subgenre — all with a touch of randomness!

No sign-ups, no API keys, no fluff — just curated exploration using public data.

---

## 🔧 Features

- 🌍 Live scraping of Wikipedia film categories by country and genre
- 🎲 Random film selection from a large, diverse dataset
- 📁 Caching system to avoid hammering Wikipedia repeatedly
- 📌 Command-line overrides for country (`-c`), genre (`-g`), and subgenre (`-s`)
- ❌ Deduplication to avoid repeated picks
- 🧠 Debug and verbose modes for diagnostics
- 📊 Clean, auto-sized table output

---

## 🚀 Quick Start

### 1. Clone the repo:
```bash
git clone https://github.com/yourusername/film-roulette.git
cd film-roulette
```

### 2. Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run it:
```bash
python roulette.py -n 5
```

---

## 🧪 Examples

### Pick 5 random films globally:
```bash
python roulette.py -n 5
```

### Pick 10 American science fiction films:
```bash
python roulette.py -c American -g "science fiction" -n 10
```

### Pick 3 French thriller films with subgenre 'political':
```bash
python roulette.py -c French -g thriller -s political -n 3
```

### Enable verbose and debug output:
```bash
python roulette.py -n 3 -v -d
```

---

## 🗂 Directory Structure

```
film-roulette/
├── cache/                      # Cached Wikipedia pages
├── roulette.py                # Main CLI program
├── requirements.txt           # Dependencies
└── README.md
```

---

## 📄 Requirements

- Python 3.7+
- Packages: `requests`, `beautifulsoup4`

---

## 🆓 License

This project has no license. It is free to use, modify, fork, or integrate however you like.

If you find it useful, a star ⭐️ or mention is always appreciated!

---

## 🧠 Future Ideas

- Export to CSV, Markdown, or JSON
- IMDb metadata lookup integration
- Filtering by content tags (e.g., animation, pornographic, etc.)
- Terminal UI (TUI) for interactive roulette

---

Made with ❤️ and a love for global cinema.

---

_“A good film is when the price of the dinner, the theatre admission and the babysitter were worth it.”_  
— Alfred Hitchcock