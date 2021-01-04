# Template for deploying ML models using Flask + Gunicorn + Nginx inside Docker

## Running the solution

In order to run this solution, you just have to install Docker, Docker compose, then clone this repository, and then:

```
bash run_docker.sh
```

For Docker installation instructions follow:

— [Docker installation](https://docs.docker.com/engine/install/ubuntu/)

— [Make Docker run without root](https://docs.docker.com/engine/install/linux-postinstall/)

— [Docker Compose installation](https://docs.docker.com/compose/install/)

## Understanding the solution

— The detailed way: check [my Medium post](https://towardsdatascience.com/how-to-deploy-ml-models-using-flask-gunicorn-nginx-docker-9b32055b3d0) regarding this solution.

— The fast way: the project is structured as follows: Flask app and WSGI entry point are localed in flask_app directory. Nginx and project configuration files are located in nginx directory. Both directories contain Docker files that are connected using docker_compose.yml file in the main directory.

For simplicity, I also added run_docker.sh file for an even easier setting-up and running this solution.

```
.
├── docker-compose.yml
├── flask_app
│   ├── Dockerfile
│   └── README.md
├── nginx
│   ├── Dockerfile
│   ├── nginx.conf
│   └── project.conf
└── run_docker.sh
```

# aws hostOS .vimrc configuration
```
set tabstop=5
set background=dark
set autoindent
set smartindent
set ruler
set shiftwidth=4
set hlsearch
set number
set paste!
set title
set history=200
set ignorecase
```
