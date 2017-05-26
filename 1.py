import sqlite3
import re
import time

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.hash import sha256_crypt
from tempfile import gettempdir

from helpers import *


from flask import jsonify

print(jsonify(matching_results=[1,2]))
