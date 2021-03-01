# warrant-game-analogy-winter2020

This is the second iteration of the Warrant Game - Analogy (WG-A) web app. This iteration was used for both studies conducted on December 2019 and January 2020.

![Participant's Interface](docs/participant-interface.PNG)

## Development Setup (Ubuntu 18.04)

### Pre-requisites

| Service    | Description                                 | Host      | Port |
| ---------- | ------------------------------------------- | --------- | ---- |
| PostgreSQL | Database Server                             | localhost | 5432 |
| Redis      | Message Broker Server (for Django Channels) | localhost | 6379 |

Notes: Look in `Project/django_project/settings.py` (lines 86-88) to find the exact PostgreSQL credentials needed.

### Steps

1. Create a Python virtual environment: `python -m virtualenv env`

2. Activate the newly created virtual environment: `source env/bin/activate`

3. Install this project's dependencies: `pip install -r requirements.txt`

4. Navigate inside the Django project directory: `cd Project/`

5. Create necessary database tables: `python manage.py migrate`

6. (Optional) Collect static files into one location: `python manage.py collectstatic`

7. Create superuser account: `python manage.py createsuperuser`

8. Run server: `python manage.py runserver`

9. Login using `127.0.0.1:8000/admin`

10. View the moderator interface at `127.0.0.1:8000/wganalogy_app/moderator/`

11. View the participant interface at `127.0.0.1:8000/wganalogy_app/user/`

## Operating the Web Application

Before creating a set of games, make sure you have a CSV file listing each and every player's username. This file will be placed in the `Project/game_sessions/` directory. Below is an example of what the project is expecting in this CSV file:

```csv
Test00
Test01
Test02
Test03
Test04
Test05
Test06
Test07
Test08
Test09
```

### Creating Games

1. Put the CSV containing player usernames in the `Project/game_sessions/` directory.
2. Login using `localhost:8000/admin`.
3. Navigate to `localhost:8000/wganalogy_app/moderator/`.
4. Fill out the form on this web page. Note that the `Game Session Name` and `Number of mTurk Workers` must correspond to the CSV you created in Step 1.

Note: Once the web application has been hosted, replace `localhost:8000` with the name of your website.

### Administering Games

You may monitor and adminster games via the `Game Sessions` and `Reports` tab in the moderator view. Under `Game Sessions`, you may view games grouped by their associated game session group.

## Notes

+ The instructional video for the experimental case is too large for GitHub.
+ In `settings.py`, note that `DEBUG=True`. For production environemnts, make sure this setting is set to `False`.
