FROM ubuntu:focal

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y gnupg apt-transport-https && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    echo "deb http://ppa.launchpad.net/deadsnakes/ppa/ubuntu focal main" >> /etc/apt/sources.list.d/deadsnakes-ubuntu-ppa-focal.list

RUN apt-get update && \
    apt-get install -y \
    apt-transport-https \
    apt-utils \
    autoconf \
    bluez \
    build-essential \
    bzip2 \
    ca-certificates \
    curl \
    dirmngr \
    freetds-bin \
    freetds-dev \
    gcc \
    gfortran \
    git \
    gnupg \
    gosu \
    iproute2 \
    krb5-user \
    latexmk \
    ldap-utils \
    libavcodec-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavutil-dev \
    libbz2-dev \
    libc-dev \
    libcurl4-openssl-dev \
    libevent-dev \
    libffi-dev \
    libglib2.0-0 \
    libglib2.0-dev \
    libkrb5-dev \
    liblapack-dev \
    liblzma-dev \
    libmemcached-dev \
    libmysqlclient-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libopenblas-dev \
    libpq-dev \
    libreadline-dev \
    libsasl2-2 \
    libsasl2-dev \
    libsasl2-modules \
    libsecp256k1-dev \
    libsm6 \
    libsnappy-dev \
    libsqlite3-dev \
    libssl-dev \
    libswresample-dev \
    libswscale-dev \
    libudev-dev \
    libxext6 \
    libxml2-dev \
    libxrender1 \
    libxslt1-dev \
    llvm \
    locales \
    lsb-release \
    make \
    nano \
    nodejs \
    openssh-client \
    pkg-config \
    postgresql-client \
    procps \
    pypy \
    python-openssl \
    python3.5 \
    python3.5-dev \
    python3.5-tk \
    python3.6 \
    python3.6-dev \
    python3.6-tk \
    python3.7 \
    python3.7-dev \
    python3.7-tk \
    python3.8 \
    python3.8-dev \
    python3.8-tk \
    python3.9 \
    python3.9-dev \
    python3.9-tk \
    sasl2-bin \
    software-properties-common \
    sqlite3 \
    sudo \
    texlive-latex-base \
    tk-dev \
    unixodbc \
    unixodbc-dev \
    virtualenv \
    wget \
    wondershaper \
    xz-utils \
    yarn \
    zlib1g-dev

RUN useradd -ms /bin/bash user && \
    echo 'user:password' | chpasswd && \
    usermod -aG sudo user

USER user

WORKDIR /home/user

COPY --chown=user subjects.json ./

COPY --chown=user experiment.py ./

COPY --chown=user subjects ./subjects

COPY --chown=user showflakes ./showflakes

RUN python3.9 experiment.py clone && \
    python3.9 experiment.py setup
