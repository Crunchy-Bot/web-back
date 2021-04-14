# web-back
Welcome to the backend API that powers most of Crunchy's infrastructure.

If you're just looking at using the api some key points:

The base domain is 
```
api.crunchy.gg/<version>
```

The current api version is `v0` as of 14/04/2021

visit [The Docs](https://api.crunchy.gg/v0/docs) for more info.

### Self Hosting
Although I highly recommend not self hosting due to the setup requiring multiple
cogs it is possible and fairly simple with Docker:

- Clone the repo
- Create a `.env` file
- Run `docker-compose up`

Providing [kratos](https://github.com/Crunchy-Bot/kratos) is running on
the same docker network and a valid PostgreSQL instance you should be good to go.


#### .env template
```
DATABASE_URL=postgresql://<username>:<password>@<db server ip>:<db sever port>/<db name>
CLIENT_ID=<discord app client ID>
CLIENT_SECRET=<discord app client secret>
BOT_AUTH=<discord OAuth2 URL>
SECURE_KEY=<A secure key for cookies>
DEBUG=True
SEARCH_DOMAIN=crunchy_kratos:9991
REDIRECT_URI=<discord oauth2 redirect uri>
BASE_URL=https://api.crunchy.gg/v0
```