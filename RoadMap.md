# 🗺️ MoviePulse Roadmap

**Version:** 2.1  
**Theme:** Smart Recommendations, Smarter Exploration  
**Tagline:** Your movie universe—curated, intelligent, and immersive.

---

## 📆 4-Week Roadmap Overview

| Week | Focus Area              | Goals                                                                 |
|------|--------------------------|-----------------------------------------------------------------------|
| 1    | 🔧 Core Functionality     | Search, movie detail, basic recs, TMDB integration                    |
| 2    | 🎨 UI/UX + AI Layer       | Sidebar filters, CineMind AI, vector recs, spoiler-free design        |
| 3    | 🌟 Premium Features       | Cinephile Mode, Date Night Mode, mood calendar, watchlist             |
| 4    | 🚀 Final Polish + Deploy  | Bug fixing, mobile testing, performance tuning, deployment            |

---

## 🔧 Week 1: Core Functionality (Foundation)

✅ Goals:
- [x] TMDB integration via `service_clients/tmdb.py`
- [x] Search functionality with autocomplete
- [x] Movie detail view with poster, metadata, overview
- [x] Basic collaborative filtering using genres and ratings
- [x] Modular Streamlit layout via `app_ui/`

📁 Deliverables:
- `/service_clients/`
- `/static_data/genres.json`
- `Home.py`, `MovieDetail.py`

---

## 🎨 Week 2: UI/UX + AI Layer (Immersion)

✅ Goals:
- [x] Sidebar filter system (genre, year, rating, mood)
- [x] Responsive dark mode layout
- [x] Vector-based similarity search (sentence-transformers)
- [x] Smart recommendations with CineMind explainability
- [x] Tooltip hints, hover animations, spoiler-free toggle

📁 Deliverables:
- `/ai_engine/`
- `/media_assets/logos/MoviePulseBanner.png`
- Streamlit state management updates

---

## 🌟 Week 3: Premium Modes (Personality)

🔄 Goals:
- [ ] Implement **Cinephile Mode**: deep-dive, trivia, director exploration
- [ ] Build **Date Night Mode**: cross-preference blending, fun UI
- [ ] Add **Mood Calendar**: calendar heatmap for movie moods
- [ ] Enable **Watchlist Save** with cookies/local storage
- [ ] Build genre, actor, and director pages with click-through navigation

📁 Deliverables:
- `premium_modes/`, `watchlist.py`
- `calendar_utils.py`, `mood_map.json`

---

## 🚀 Week 4: Final Polish + Deployment

🔄 Goals:
- [ ] Full UI polish, mobile testing
- [ ] Load time and memory optimizations
- [ ] Interactive tutorial for first-time users
- [ ] Unit tests in `/tests/` with `pytest`
- [ ] Cloud deployment (Streamlit Community Cloud, optional Hugging Face Spaces)

📁 Deliverables:
- `tests/test_ai_engine.py`
- `pages/Tutorial.py`
- `.streamlit/config.toml`

---

## 🎯 Final Goals

- [ ] ✅ A smart, immersive movie discovery app with hybrid recommendations
- [ ] ✅ Personalized flows: search-based and filter-based
- [ ] ✅ Premium experiences (Cinephile Mode, Date Night, Mood Calendar)
- [ ] ✅ Open for AI-powered enhancements and user personalization

---

## 📌 Notes

- This roadmap is modular — individual features can be developed and shipped independently.
- Each week includes time for review, testing, and feedback integration.
- Ideas? Open an [Issue](https://github.com/jaymwangi93/MoviePulse/issues) or contribute via Pull Request.

---

> Built with ❤️ by [GlitaJay]
