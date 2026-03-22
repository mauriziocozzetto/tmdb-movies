from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from typing import List
import requests
import os

app = FastAPI()

# --- CONFIGURAZIONE PERCORSI ---
# Otteniamo il percorso assoluto della cartella dove si trova main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Definiamo il percorso della cartella static
STATIC_DIR = os.path.join(BASE_DIR, "static")

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TMDB_API_KEY = "2fa8ef75c70a212d9fd3cd51b785939f"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMG_PLACEHOLDER = "https://placehold.jp/24/032541/01b4e4/300x450.png?text=Immagine%20ND"

# --- MODELLI ---

class Movie(BaseModel):
    id: int
    title: str = "N.D."
    release_date: str = "N.D."
    vote_average: float = 0.0
    poster_path: str = ""

    @field_validator("release_date", mode="before")
    @classmethod
    def extract_year(cls, v):
        return v[:4] if v and len(str(v)) >= 4 else "N.D."

    @field_validator("poster_path", mode="before")
    @classmethod
    def format_img(cls, v):
        if not v or str(v) in ["None", "", "null", None]:
            return IMG_PLACEHOLDER
        return f"https://image.tmdb.org/t/p/w342{v}"

class DirectorInfo(BaseModel):
    id: int
    name: str

class ActorInMovie(BaseModel):
    id: int
    name: str
    character: str = "N.D."
    profile_path: str = ""

    @field_validator("profile_path", mode="before")
    @classmethod
    def format_img(cls, v):
        if not v or str(v) in ["None", "", "null", None]:
            return IMG_PLACEHOLDER
        return f"https://image.tmdb.org/t/p/w185{v}"

class MovieDetail(Movie):
    overview: str = "Nessuna sinossi disponibile."
    registi: List[DirectorInfo] = []

    @field_validator("overview", mode="before")
    @classmethod
    def validate_overview(cls, v):
        if not v or str(v).strip() in ["", "None", "null", None]:
            return "Nessuna sinossi disponibile per questo film in italiano."
        return v

class ActorDetail(BaseModel):
    id: int
    name: str = "N.D."
    birthday: str = "N.D."
    place_of_birth: str = "N.D."
    biography: str = "Nessuna biografia disponibile."
    profile_path: str = ""

    @field_validator("birthday", "place_of_birth", "biography", mode="before")
    @classmethod
    def validate_nulls(cls, v):
        if v is None or str(v).strip() in ["", "None", "null", None]:
            return "Informazione non disponibile"
        return v

    @field_validator("profile_path", mode="before")
    @classmethod
    def format_img(cls, v):
        if not v or str(v) in ["None", "", "null", None]:
            return IMG_PLACEHOLDER
        return f"https://image.tmdb.org/t/p/w500{v}"

# --- API ---

@app.get("/api/movies/trending")
async def get_trending():
    r = requests.get(f"{TMDB_BASE_URL}/trending/movie/week",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT"}).json()
    return [Movie(**m) for m in r.get("results", [])[:10]]

@app.get("/api/movies/title={title}")
async def search(title: str):
    r = requests.get(f"{TMDB_BASE_URL}/search/movie",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT", "query": title}).json()
    return [Movie(**m) for m in r.get("results", [])]

@app.get("/api/movies/{id}")
async def movie_details(id: int):
    resp = requests.get(f"{TMDB_BASE_URL}/movie/{id}",
                        params={"api_key": TMDB_API_KEY, "language": "it-IT"})
    if resp.status_code != 200:
        raise HTTPException(status_code=404)
    m_data = resp.json()
    c_data = requests.get(f"{TMDB_BASE_URL}/movie/{id}/credits",
                          params={"api_key": TMDB_API_KEY}).json()
    regs = [DirectorInfo(**p) for p in c_data.get("crew", [])
            if p.get("job") == "Director"]
    # Assicuriamoci che registi sia sempre una lista, anche vuota
    return MovieDetail(**m_data, registi=regs if regs else [])

@app.get("/api/movies/{id}/actors")
async def movie_cast(id: int):
    r = requests.get(f"{TMDB_BASE_URL}/movie/{id}/credits",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT"}).json()
    return [ActorInMovie(**p) for p in r.get("cast", [])[:12]]

@app.get("/api/actors/{id}")
async def person_details(id: int):
    resp = requests.get(f"{TMDB_BASE_URL}/person/{id}",
                        params={"api_key": TMDB_API_KEY, "language": "it-IT"})
    if resp.status_code != 200:
        raise HTTPException(status_code=404)
    return ActorDetail(**resp.json())

@app.get("/api/actors/{id}/movies")
@app.get("/api/directors/{id}/movies")
async def person_movies(id: int):
    r = requests.get(f"{TMDB_BASE_URL}/person/{id}/movie_credits",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT"}).json()
    data = r.get("cast", []) + [m for m in r.get("crew", [])
                                if m.get("job") == "Director"]
    return [Movie(**m) for m in data]

# --- SERVIZIO FILE STATICI ---
# Montiamo la cartella static per file CSS/JS/Img se presenti
app.mount("/static_files", StaticFiles(directory=STATIC_DIR), name="static_files")

# Rotte esplicite per le pagine HTML usando percorsi assoluti
@app.get("/")
async def serve_home(): 
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/index.html")
async def serve_index(): 
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/movie.html")
async def serve_movie_page(): 
    return FileResponse(os.path.join(STATIC_DIR, "movie.html"))

@app.get("/actor.html")
async def serve_actor_page(): 
    return FileResponse(os.path.join(STATIC_DIR, "actor.html"))

@app.get("/director.html")
async def serve_director_page(): 
    return FileResponse(os.path.join(STATIC_DIR, "director.html"))
