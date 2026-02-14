# Aggiungi RedirectResponse
from fastapi.responses import FileResponse, RedirectResponse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional
import requests

app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_methods=["*"],
                   allow_headers=["*"])

TMDB_API_KEY = "2fa8ef75c70a212d9fd3cd51b785939f"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
IMG_ND = "https://placehold.jp/24/032541/01b4e4/300x450.png?text=Immagine%20ND"
INFO_ND = "Informazione non disponibile"

# --- MODELLI ROBUSTI ---


class Film(BaseModel):
    id: int
    title: str = INFO_ND
    release_date: str = INFO_ND
    poster_path: str = IMG_ND
    vote_average: float = 0.0
    overview: str = INFO_ND

    @field_validator("title", "overview", mode="before")
    @classmethod
    def validate_text(cls, v):
        return v if v and str(v).strip() not in ["", "None", "null"] else INFO_ND

    @field_validator("release_date", mode="before")
    @classmethod
    def extract_year(cls, v):
        # Se la data esiste ed è lunga almeno 4 caratteri, prendi solo l'anno
        if v and len(str(v)) >= 4:
            return str(v)[:4]
        return INFO_ND

    @field_validator("poster_path", mode="before")
    @classmethod
    def validate_img(cls, v):
        if not v or str(v) in ["None", "", "null"]:
            return IMG_ND
        return f"https://image.tmdb.org/t/p/w342{v}"


class Person(BaseModel):
    id: int
    name: str = INFO_ND
    character: Optional[str] = INFO_ND
    profile_path: str = IMG_ND
    biography: str = INFO_ND
    birthday: str = INFO_ND
    place_of_birth: str = INFO_ND

    @field_validator("name", "character", "biography", "birthday", "place_of_birth", mode="before")
    @classmethod
    def validate_text(cls, v):
        return v if v and str(v).strip() not in ["", "None", "null"] else INFO_ND

    @field_validator("profile_path", mode="before")
    @classmethod
    def validate_img(cls, v):
        if not v or str(v) in ["None", "", "null"]:
            return IMG_ND
        return f"https://image.tmdb.org/t/p/w185{v}"

# --- HELPER ---


def tmdb_get(path: str, params: dict = {}):
    params.update({"api_key": TMDB_API_KEY, "language": "it-IT"})
    r = requests.get(f"{TMDB_BASE_URL}/{path}", params=params)
    if r.status_code != 200:
        raise HTTPException(status_code=404)
    return r.json()

# --- ROTTE ---


@app.get("/api/films/trendings")
async def trend():
    data = tmdb_get("trending/movie/week")
    return [Film(**m) for m in data.get("results", [])[:10]]


@app.get("/api/films/search")
async def search(title: str):
    data = tmdb_get("search/movie", {"query": title})
    return [Film(**m) for m in data.get("results", [])]


@app.get("/api/films/{fid}")
async def film_info(fid: int):
    data = tmdb_get(f"movie/{fid}")
    return Film(**data)


@app.get("/api/films/{fid}/actors")
async def film_actors(fid: int):
    data = tmdb_get(f"movie/{fid}/credits")
    return [Person(**p) for p in data.get("cast", [])[:12]]


@app.get("/api/films/{fid}/directors")
async def film_directors(fid: int):
    data = tmdb_get(f"movie/{fid}/credits")
    # Filtriamo chi ha il ruolo di Director nella crew
    return [Person(**p) for p in data.get("crew", []) if p.get("job") == "Director"]


@app.get("/api/actors/{aid}/films")
async def actor_films(aid: int):
    data = tmdb_get(f"person/{aid}/movie_credits")
    return [Film(**m) for m in data.get("cast", [])]

# ROTTA SIMMETRICA: Film diretti dal regista


@app.get("/api/directors/{did}/films")
async def director_films(did: int):
    data = tmdb_get(f"person/{did}/movie_credits")
    # Prendiamo solo i film in cui la persona compare come Director
    films = [m for m in data.get("crew", []) if m.get("job") == "Director"]
    return [Film(**m) for m in films]


@app.get("/api/directors/{did}")
async def director_info(did: int):
    data = tmdb_get(f"person/{did}")
    return Person(**data)


@app.get("/api/actors/{aid}")
async def actor_info(aid: int):
    return Person(**tmdb_get(f"person/{aid}"))

app.mount("/static", StaticFiles(directory="static"), name="static")


# --- ROTTE PER SERVIRE LE PAGINE HTML ---


@app.get("/")
async def home():
    return FileResponse("static/index.html")


@app.get("/movie.html")
async def movie_page(id: Optional[str] = None):
    # 1. Se l'id manca o è una stringa vuota
    if not id:
        return RedirectResponse(url="/")

    # 2. Verifica se l'ID è un numero e se esiste su TMDB
    try:
        fid = int(id)
        # Se il film non esiste, solleva HTTPException 404
        tmdb_get(f"movie/{fid}")
        return FileResponse("static/movie.html")
    except (ValueError, HTTPException):
        # In caso di ID non numerico o film inesistente, torna alla Home
        return RedirectResponse(url="/")


@app.get("/actor.html")
async def actor_page(id: Optional[str] = None):
    if not id:
        return RedirectResponse(url="/")
    try:
        aid = int(id)
        tmdb_get(f"person/{aid}")
        return FileResponse("static/actor.html")
    except (ValueError, HTTPException):
        return RedirectResponse(url="/")


@app.get("/director.html")
async def director_page(id: Optional[str] = None):
    if not id:
        return RedirectResponse(url="/")
    try:
        did = int(id)
        tmdb_get(f"person/{did}")
        return FileResponse("static/director.html")
    except (ValueError, HTTPException):
        return RedirectResponse(url="/")
