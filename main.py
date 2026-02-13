from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import requests

app = FastAPI()

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
    titolo: str
    anno_uscita: str
    percentuale_gradimento: int
    locandina: str


class DirectorInfo(BaseModel):
    id: int
    nome: str


class ActorInMovie(BaseModel):
    id: int
    nome: str
    ruolo: str
    locandina: str


class MovieDetail(BaseModel):
    id: int
    titolo: str
    anno_uscita: str
    percentuale_gradimento: int
    locandina: str
    sinossi: str
    registi: List[DirectorInfo]


class ActorDetail(BaseModel):
    id: int
    nome: str
    data_nascita: str
    luogo_nascita: str
    biografia: str
    locandina: str

# --- UTILITY ---


def format_img(path, size="w500"):
    # Se il path è nullo, vuoto o la stringa "None", restituiamo subito il placeholder
    if not path or str(path) == "None" or str(path).strip() == "":
        return IMG_PLACEHOLDER
    return f"https://image.tmdb.org/t/p/{size}{path}"


def get_y(d):
    return d[:4] if d and len(d) >= 4 else "N.D."


def validate_text(text, fallback="Informazione non disponibile."):
    if not text or str(text).strip() == "" or str(text) == "None":
        return fallback
    return text

# --- API ---


@app.get("/api/movies/trending")
async def get_trending():
    r = requests.get(f"{TMDB_BASE_URL}/trending/movie/week",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT"}).json()
    return [Movie(id=m["id"], titolo=m.get("title", "N.D."), anno_uscita=get_y(m.get("release_date")), percentuale_gradimento=int(m.get("vote_average", 0)*10), locandina=format_img(m.get("poster_path"), "w342")) for m in r.get("results", [])[:10]]


@app.get("/api/movies/title={title}")
async def search(title: str):
    r = requests.get(f"{TMDB_BASE_URL}/search/movie", params={
                     "api_key": TMDB_API_KEY, "language": "it-IT", "query": title}).json()
    return [Movie(id=m["id"], titolo=m.get("title", "N.D."), anno_uscita=get_y(m.get("release_date")), percentuale_gradimento=int(m.get("vote_average", 0)*10), locandina=format_img(m.get("poster_path"), "w342")) for m in r.get("results", [])]


@app.get("/api/movies/{id}")
async def movie_details(id: int):
    m = requests.get(f"{TMDB_BASE_URL}/movie/{id}",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT"}).json()
    c = requests.get(f"{TMDB_BASE_URL}/movie/{id}/credits",
                     params={"api_key": TMDB_API_KEY}).json()
    regs = [DirectorInfo(id=p["id"], nome=p["name"])
            for p in c.get("crew", []) if p.get("job") == "Director"]
    return MovieDetail(
        id=m["id"],
        titolo=m.get("title", "N.D."),
        anno_uscita=get_y(m.get("release_date")),
        percentuale_gradimento=int(m.get("vote_average", 0)*10),
        locandina=format_img(m.get("poster_path")),
        sinossi=validate_text(
            m.get("overview"), "Nessuna sinossi disponibile in italiano."),
        registi=regs if regs else [DirectorInfo(id=0, nome="N.D.")]
    )


@app.get("/api/movies/{id}/actors")
async def movie_cast(id: int):
    c = requests.get(f"{TMDB_BASE_URL}/movie/{id}/credits",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT"}).json()
    return [ActorInMovie(id=p["id"], nome=p["name"], ruolo=p.get("character", "N.D."), locandina=format_img(p.get("profile_path"), "w185")) for p in c.get("cast", [])[:12]]


@app.get("/api/actors/{id}")
async def person_details(id: int):
    a = requests.get(f"{TMDB_BASE_URL}/person/{id}",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT"}).json()
    return ActorDetail(
        id=a["id"],
        nome=a["name"],
        data_nascita=validate_text(a.get("birthday"), "N.D."),
        luogo_nascita=validate_text(a.get("place_of_birth"), "N.D."),
        biografia=validate_text(
            a.get("biography"), "Nessuna biografia disponibile in italiano."),
        locandina=format_img(a.get("profile_path"))
    )


@app.get("/api/actors/{id}/movies")
async def actor_filmography(id: int):
    r = requests.get(f"{TMDB_BASE_URL}/person/{id}/movie_credits",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT"}).json()
    cast = sorted(r.get("cast", []), key=lambda x: x.get(
        "release_date", ""), reverse=True)
    return [Movie(id=m["id"], titolo=m.get("title", "N.D."), anno_uscita=get_y(m.get("release_date")), percentuale_gradimento=int(m.get("vote_average", 0)*10), locandina=format_img(m.get("poster_path"), "w342")) for m in cast]


@app.get("/api/directors/{id}/movies")
async def director_filmography(id: int):
    r = requests.get(f"{TMDB_BASE_URL}/person/{id}/movie_credits",
                     params={"api_key": TMDB_API_KEY, "language": "it-IT"}).json()
    crew = r.get("crew", [])
    directors_list = [m for m in crew if m.get("job") == "Director"]
    sorted_films = sorted(directors_list, key=lambda x: x.get(
        "release_date", ""), reverse=True)
    return [Movie(id=m["id"], titolo=m.get("title", "N.D."), anno_uscita=get_y(m.get("release_date")), percentuale_gradimento=int(m.get("vote_average", 0)*10), locandina=format_img(m.get("poster_path"), "w342")) for m in sorted_films]

# --- SERVIZIO FILE STATICI ---
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def serve_home(): return FileResponse("static/index.html")
@app.get("/index.html")
async def serve_index(): return FileResponse("static/index.html")
@app.get("/movie.html")
async def serve_movie_page(): return FileResponse("static/movie.html")
@app.get("/actor.html")
async def serve_actor_page(): return FileResponse("static/actor.html")
@app.get("/director.html")
async def serve_director_page(): return FileResponse("static/director.html")
