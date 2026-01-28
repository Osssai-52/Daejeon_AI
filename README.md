# Daejoen_AI

graph TD
    %% Frontend Cluster
    subgraph "Frontend Client (Browser)"
        UI[React + shadcn/ui UI]
        State[TanStack Query State Mgt]
        Map[Mapbox GL Map View]
        ThreeD[R3F/Spline 3D Visuals]
        Axios[Axios HTTP Client]
    end

    %% Backend Cluster
    subgraph "Backend Server (Uvicorn/FastAPI)"
        API[FastAPI Router & Auth Middleware]
        
        subgraph "Services Layer"
            AuthSvc[Auth Service (JWT)]
            RecSvc[Recommendation Service]
            RouteSvc[Routing Algorithm (Greedy)]
            AISvc[AI Service (CLIP Model / PyTorch)]
        end
        
        ORM[SQLAlchemy ORM]
    end

    %% Data & External Services Cluster
    subgraph "Data & External Services"
        DB[(PostgreSQL + pgvector)]
        S3[AWS S3 Bucket (Images)]
        Kakao[Kakao Auth API]
        MapboxAPI[Mapbox Tile Servers]
    end

    %% Connections - Frontend Internal
    UI --> State
    UI --> Map
    UI --> ThreeD
    State --> Axios
    Map --> MapboxAPI

    %% Connections - Client to Server
    Axios -- "REST API Requests (JSON/Multipart)" --> API

    %% Connections - Backend Internal
    API --> AuthSvc
    API --> RecSvc
    API --> RouteSvc
    RecSvc --> AISvc
    RecSvc --> ORM
    RouteSvc --> ORM
    AuthSvc --> ORM

    %% Connections - Backend to External
    AuthSvc -- "OAuth 2.0 Validation" --> Kakao
    API -- "Image Upload/Read" --> S3
    ORM -- "Vector Search & CRUD" --> DB
    AISvc -. "Load Model" .-> S3

    %% Styling
    classDef frontend fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef backend fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    classDef data fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef ai fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,stroke-dasharray: 5 5;

    class UI,State,Map,ThreeD,Axios frontend;
    class API,AuthSvc,RecSvc,RouteSvc,ORM backend;
    class DB,S3,Kakao,MapboxAPI data;
    class AISvc ai;