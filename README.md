

```markdown
<p align="center">
  <img src="media_assets/logos/MoviePulseBanner.png" alt="MoviePulse Banner" width="100%" />
</p>

<h1 align="center">🎬 MoviePulse v2.1</h1>
<p align="center"><em>Your movie universe — curated, intelligent, and immersive.</em></p>

---

## 🌟 Overview

**MoviePulse** is a smart and immersive movie recommendation platform powered by AI and built with Streamlit. It fuses intelligent filtering, hybrid recommenders, and a cinematic UI to help users discover, explore, and enjoy movies tailored to their tastes.

This project leverages TMDB data, NLP embeddings, explainability layers, and contextual personalization to craft a seamless and intelligent movie experience.

---

## 🚀 Key Features

- 🔍 **Search & Discover** – Instant search with intelligent suggestions
- 🎞️ **Smart Recommendations** – Hybrid engine using embeddings, genres, and mood metadata
- 🧠 **CineMind AI** – Explainable recommendations with contextual awareness
- 🗂️ **Sidebar Filters** – Intuitive filters for genres, moods, ratings, release year, etc.
- 🧑‍🤝‍🧑 **Cinephile & Date Night Modes** – Personalized flows for individuals and couples
- 📅 **Mood Calendar & Watchlist** – Plan and save your movie lineups
- ✨ **Immersive UI** – Dark mode, spoiler-free mode, hover animations
- 📊 **Analytics + A/B Testing** – Track engagement and optimize recommendations
- ♿ **Accessibility Options** – Dyslexia-friendly fonts and minimalist themes

---

## 📁 Project Structure

```

moviepulse/
├── app.py                      # Streamlit entry point
├── .env                        # Local environment secrets
├── README.md                   # Overview, setup, features
├── requirements.txt            # Python dependencies
│
├── .streamlit/                 # Theme and UI config
│   └── config.toml
│
├── core\_config/
│   ├── app\_settings.py         # Global feature toggles and config
│   ├── constants.py            # Static mappings (genres, moods)
│   └── local\_secrets.toml
│
├── media\_assets/
│   ├── logos/                  # App logos and banner
│   ├── posters/                # Cached TMDB posters
│   ├── icons/                  # SVG icons for UI
│   ├── audio/                  # Optional ambient sounds
│   ├── styles/                 # Custom CSS
│   └── translations/           # Multilingual strings (optional)
│
├── streamlit\_pages/
│   ├── 1\_🏠\_Home.py
│   ├── 2\_🔍\_Search.py
│   ├── 3\_🎬\_MovieDetails.py
│   ├── 4\_⭐*Watchlist.py
│   ├── 5\_🎭\_ActorProfile.py
│   ├── 6\_🎞️\_GenreView\.py
│   ├── 7\_🎯\_CinephileMode.py
│   ├── 8\_📅\_MoodCalendar.py
│   └── 9*⚙️\_UserSettings.py
│
├── ui\_components/
│   ├── HeaderBar.py
│   ├── SidebarFilters.py
│   ├── SearchInput.py
│   ├── MovieTile.py
│   ├── MovieGridView\.py
│   ├── SmartTagDisplay.py
│   ├── QuickSummary.py
│   ├── CastList.py
│   └── ToastNotifications.py
│
├── ai\_smart\_recommender/
│   ├── recommender\_engine/
│   │   ├── core\_logic/
│   │   ├── strategy\_interfaces/
│   │   ├── diversity\_control/
│   │   └── orchestrator.py
│   ├── user\_personalization/
│   ├── rule\_based\_backup/
│   ├── explainability\_layer/
│   └── recommender\_utilities/
│
├── ai\_local\_modules/
│   ├── smart\_recommender.py
│   ├── vibe\_analysis.py
│   ├── tldr\_summarizer.py
│   ├── tag\_inference.py
│   └── planner\_logic.py
│
├── service\_clients/
│   ├── tmdb\_client.py
│   ├── local\_store.py
│   ├── file\_cache.py
│   └── diagnostics\_logger.py
│
├── static\_data/
│   ├── genres.json
│   ├── moods.json
│   ├── actors.json
│   └── theme\_presets.json
│
├── session\_utils/
│   ├── session\_helpers.py
│   ├── state\_tracker.py
│   ├── log\_config.py
│   └── url\_formatting.py
│
├── app\_tests/
│   ├── test\_tmdb\_client.py
│   ├── test\_smart\_recommender.py
│   ├── test\_ui\_components.py
│   └── test\_watchlist\_logic.py
│
├── deployment\_config/
│   ├── streamlit\_deploy.toml
│   └── Dockerfile
│
├── dev\_scripts/
│   ├── ingest\_genre\_data.py
│   ├── prewarm\_assets.py
│   └── init\_local\_db.py
│
└── RoadMap.md                  # 28-day dev plan and milestones

````

---

## ⚙️ Setup Instructions

1. **Clone the repository**  
   ```bash
   git clone https://github.com/yourusername/MoviePulse.git
   cd MoviePulse
````

2. **Create and activate a virtual environment**

   ```bash
   python -m venv pulse-env
   # On Windows:
   pulse-env\Scripts\activate
   # On Unix/macOS:
   source pulse-env/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   Create a `.env` file and add your TMDB key:

   ```
   TMDB_API_KEY=your_tmdb_api_key
   ```

5. **Run the app**

   ```bash
   streamlit run app.py
   ```

---

## 🗺️ Development Roadmap

See [`RoadMap.md`](RoadMap.md) for the full 28-day development plan, feature priorities, testing goals, and deployment pipeline.

---

## 🧪 Requirements Snapshot

> Auto-generated from latest build:

```
streamlit
requests
python-dotenv
scikit-learn
sentence-transformers
scipy
pandas
numpy
Pillow
streamlit-extras
streamlit-option-menu
streamlit-js-eval
streamlit-cookies-manager
pytest
loguru
orjson
openai
matplotlib
plotly
```

---

## 📸 Screenshots (Coming Soon)

* Home interface with themed search
* Smart recommendations view
* Mood calendar with watchlist integration
* Cinephile Mode and Date Night view

---

## 🙌 Contributions

Open to feature suggestions, collaborations, and community feedback!
Feel free to fork, open issues, or submit PRs.

---

## 📜 License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for more details.

```
