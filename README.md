<p align="center">
  <p align="center">
    <img src="https://nng.alonas.lv/img/logo.svg" height="100">
  </p>
  <h1 align="center">nng tasks</h1>
</p>

[![License badge](https://img.shields.io/badge/license-EUPL-blue.svg)](LICENSE)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docker Build and Push](https://github.com/thealonas/nng-tasks/actions/workflows/docker.yml/badge.svg)](https://github.com/thealonas/nng-tasks/actions/workflows/docker.yml)

A script that automates actions aimed at working with nng groups themselves (cleaning comments, deleting inactive members, updating the ban list, etc.). Unlike other scripts, it bypasses the nng api and works directly with the database.

### Installation

Use a pre-built [Docker container](https://github.com/orgs/thealonas/packages/container/package/nng-tasks).

### Configuration

The main configuration is done through the environment variables.

* `NNG_DB_URL` — Link to PostgreSQL database
* `OP_CONNECT_HOST` - Link to 1Password Connect server
* `OP_CONNECT_TOKEN` - 1Password Connect token
