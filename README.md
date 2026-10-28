# 🤝 Enterprise Knowledge Base: Chat With Your PDFs

An AI-powered document assistant. Sign in, upload your company PDFs, and ask questions in plain English. Answers are generated only from your documents.

Built with **Streamlit, LangChain, OpenAI and FAISS**.

## Features

- **Authentication**: sign up, sign in and forgot / reset password (email + password only). Passwords are hashed with bcrypt
- **Bring your own API key**: users enter their OpenAI API key from the 🔑 button at the top right of the page. The key is kept in the browser session only and is never saved to disk
- **Conversation memory**: follow-up questions such as "What does that mean?" are understood in the context of the current chat
- **Persistent chat history**: chats are saved per user in SQLite, so they are still there after a page refresh and a new sign in
- Animated UI with light and dark theme support

## How it works

```
PDF upload -> text extraction -> chunking -> embeddings (OpenAI) -> FAISS index
Question -> rewritten as a standalone question using chat history
         -> top 3 matching chunks retrieved -> LLM answer
```

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit app (UI, chat, API key menu) |
| `auth_ui.py` | Sign in, sign up and password reset pages |
| `database.py` | SQLite storage for users, reset codes and chat history |
| `email_service.py` | Sends password reset emails over SMTP |
| `memory_creation_for_llm.py` | PDF loading, chunking and FAISS indexing |
| `connect_memory_with_llm.py` | Retrieval chain and chat memory |
| `requirements.txt` | Python dependencies |
| `.env.example` | Example environment variables |

## Setup

**Requirements:** Python 3.10 or newer and an OpenAI API key.

```bash
# 1. Clone the repository and open the folder
git clone <your-repo-url>
cd <your-repo-folder>

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) create your environment file
cp .env.example .env

# 5. Run the app
streamlit run app.py
```

## Usage

1. Create an account and sign in.
2. Click **🔑 API Key** (top right) and paste your OpenAI API key.
3. Upload PDFs in the sidebar and click **Process Documents**.
4. Ask questions in the chat box.

## Configuration

All variables are optional and go in a `.env` file:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Fallback key, used when a user has not entered their own |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Mail server used to send password reset codes |
| `APP_DB_FILE` | SQLite database path (default `app_data.db`) |

### Password reset emails

When SMTP is configured, a 6-digit code (valid for 15 minutes) is emailed to the user. When SMTP is **not** configured, the app runs in **demo mode** and shows the code on the screen. Always configure SMTP before a real deployment. For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833).

## Security notes

- Passwords are hashed with bcrypt; reset codes are stored hashed and expire after 15 minutes
- Login attempts are rate limited (5 failures lock the form for 60 seconds)
- Each user only sees their own chat history
- API keys are stored in session memory only

## Known limitations

- The uploaded PDFs (`data/`) and the vector index (`vectorstore/`) are shared by all users of the app
- Reloading the browser tab signs the user out (chat history is kept and returns after signing in again)
- Scanned PDFs (images) need OCR before they can be indexed
- On hosts with temporary storage, the SQLite database, `data/` and `vectorstore/` are reset when the app restarts

## License

MIT
