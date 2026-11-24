# Current project notes

- Customer portal, admin dashboard, and Technical Inspector are served by the React application in `web/`.
- FastAPI in `src/api/` remains the backend and shares conversations with Gemini-only orchestration.
- Customer-facing generated messages use Google Gemini 2.5 Flash. When Gemini fails, the API returns an error and does not send a canned reply.
- Configure `GEMINI_API_KEY` in the API environment. See `README.md` for run commands.
