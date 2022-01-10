#!/bin/bash

uwsgi --http 0.0.0.0:5000 --module ambience.app:app
