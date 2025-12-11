## 📦 Imagens

```bash
# listar imagens locais
docker images

# baixar (pull) uma imagem
docker pull nome_da_imagem:tag

# remover imagem
docker rmi nome_da_imagem:tag

# construir imagem a partir de um Dockerfile
docker build -t nome_da_imagem:tag .

# ver histórico da imagem
docker history nome_da_imagem:tag
```

---

## 🧱 Containers

```bash
# listar containers rodando
docker ps

# listar TODOS containers (inclusive parados)
docker ps -a

# iniciar um container
docker start nome_ou_id

# parar um container
docker stop nome_ou_id

# reiniciar um container
docker restart nome_ou_id

# remover container
docker rm nome_ou_id

# criar e rodar um container (-d = detach)
docker run -d --name meu_container nome_da_imagem:tag

# rodar um container e abrir terminal interativo
docker run -it --name meu_container nome_da_imagem:tag /bin/bash
```

---

## 🔍 Logs, shell e inspeção

```bash
# ver logs de um container
docker logs nome_ou_id

# ver logs e seguir em tempo real
docker logs -f nome_ou_id

# entrar no container (shell)
docker exec -it nome_ou_id /bin/bash
# em alpine:
docker exec -it nome_ou_id /bin/sh

# inspecionar container (detalhes de rede, mounts, etc.)
docker inspect nome_ou_id
```

---

## 🗂 Volumes

```bash
# listar volumes
docker volume ls

# inspecionar volume
docker volume inspect nome_do_volume

# remover volume
docker volume rm nome_do_volume

# remover volumes “órfãos” (sem container usando)
docker volume prune
```

---

## 🌐 Redes

```bash
# listar redes
docker network ls

# inspecionar rede
docker network inspect nome_da_rede

# criar rede
docker network create minha_rede

# remover rede
docker network rm nome_da_rede
```

---

## 🧩 Docker Compose (nova sintaxe)

No teu caso você está usando **`docker compose`** (sem hífen).

```bash
# subir tudo definido no docker-compose.yml
docker compose up

# subir tudo e reconstruir imagens
docker compose up --build

# rodar em segundo plano
docker compose up -d

# parar e remover containers, mas manter volumes
docker compose down

# ver logs de todos serviços
docker compose logs

# seguir logs em tempo real
docker compose logs -f

# logs de um serviço específico
docker compose logs order-service

# reconstruir só um serviço
docker compose build order-service

# reiniciar só um serviço
docker compose restart order-service
```

---

## 🧹 Limpeza geral

```bash
# remover containers parados, redes não usadas, imagens dangling e caches
docker system prune

# incluir volumes na limpeza (CUIDADO!)
docker system prune -a --volumes
```