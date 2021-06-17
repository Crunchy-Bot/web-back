import enum

import asyncpg

import router

from typing import List

from server import Backend
from utils.responders import StandardResponse

from pydantic import BaseModel, constr, validator


VarChar32 = constr(min_length=1, max_length=32, strip_whitespace=True)


class Command(BaseModel):
    command_id: VarChar32
    name: VarChar32
    category: VarChar32
    about: str
    running: str
    user_required_permissions: int
    bot_required_permissions: int

    @validator("command_id")
    def convert_id(cls, val: str):
        return val.lower().replace(" ", "-")

    @validator("category")
    def convert_cat(cls, val: str):
        return val.lower().replace(" ", "-")


class CommandsResponse(StandardResponse):
    data: List[Command]


class CommandsBlueprint(router.Blueprint):
    __base_route__ = "/commands"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/list",
        endpoint_name="Get All Commands",
        methods=["GET"],
        response_model=CommandsResponse,
        tags=["Commands"]
    )
    async def list_commands(self):
        results = await self.app.pool.fetch("""
            SELECT * FROM commands;
        """)

        return CommandsResponse(status=200, data=list(map(dict, results)))  # noqa

    @router.endpoint(
        "/edit",
        endpoint_name="Add Command",
        methods=["POST"],
        response_model=StandardResponse,
        tags=["Commands"]
    )
    async def add_command(self, payload: Command):
        # todo auth

        await self.app.pool.execute(
            """
            INSERT INTO commands (
                command_id, 
                name, 
                category, 
                about, 
                running, 
                user_required_permissions, 
                bot_required_permissions
            ) VALUES ($1, $2, $3, $4, $5, $6, $7);
            """,
            payload.command_id, payload.name,
            payload.category, payload.about,
            payload.running, payload.user_required_permissions,
            payload.bot_required_permissions,
        )

        return StandardResponse(
            status=200,
            data=f"successfully inserted command {payload.command_id}",
        )

    @router.endpoint(
        "/edit",
        endpoint_name="Remove Command",
        methods=["DELETE"],
        response_model=StandardResponse,
        tags=["Commands"]
    )
    async def remove_command(self, command_id: VarChar32):
        # todo auth

        await self.app.pool.execute("""
            DELETE FROM commands WHERE command_id = $1;
        """, command_id)

        return StandardResponse(
            status=200,
            data=f"successfully deleted command if exists {command_id}",
        )


class CommandAlias(BaseModel):
    command_id: VarChar32
    alias: VarChar32

    name: VarChar32 = None
    category: VarChar32 = None

    @validator("command_id")
    def convert_id(cls, val: str):
        return val.lower().replace(" ", "-")


class AliasesResponse(StandardResponse):
    data: List[CommandAlias]


class AliasCopyResponse(StandardResponse):
    data: List[dict]


class AliasCopyTarget(enum.Enum):
    guild = "guild"
    user = "user"


class CommandUserAliasesBlueprint(router.Blueprint):
    __base_route__ = "/commands/aliases/users"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/{user_id:int}",
        endpoint_name="Get User Aliases",
        methods=["GET"],
        response_model=AliasesResponse,
        tags=["Command User Aliases"]
    )
    async def get_aliases(self, user_id: int):
        """ Gets the aliases for the given user. """
        # todo auth

        results = await self.app.pool.fetch("""
            SELECT 
                user_command_aliases.alias,
                user_command_aliases.command_id, 
                commands.name,
                commands.category
            FROM user_command_aliases
            INNER JOIN commands 
            ON commands.command_id = user_command_aliases.command_id
            WHERE 
                user_command_aliases.user_id = $1;
        """, user_id)

        return AliasesResponse(status=200, data=list(map(dict, results)))  # noqa

    @router.endpoint(
        "/{user_id:int}/edit",
        endpoint_name="Add User Alias",
        methods=["POST"],
        response_model=StandardResponse,
        tags=["Command User Aliases"]
    )
    async def add_aliases(self, user_id: int, payload: CommandAlias):
        """ Adds an alias for the given user. """
        # todo auth

        fut = self.app.pool.execute("""
            INSERT INTO user_command_aliases (user_id, command_id, alias) 
            VALUES ($1, $2, $3);
        """, user_id, payload.command_id, payload.alias)

        try:
            await fut
        except asyncpg.ForeignKeyViolationError:
            return StandardResponse(
                status=422,
                data=f"command with command id {payload.command_id} does not exist",
            ).into_response()

        return StandardResponse(
            status=200,
            data=f"alias added for command id {payload.command_id}",
        )

    @router.endpoint(
        "/{user_id:int}/edit",
        endpoint_name="Remove User Alias",
        methods=["DELETE"],
        response_model=StandardResponse,
        tags=["Command User Aliases"],
    )
    async def remove_aliases(
        self,
        user_id: int,
        alias: VarChar32 = None,
        command_id: VarChar32 = None,
    ):
        """ Removes an alias from the given user. """
        # todo auth

        if command_id is not None and alias is not None:
            return StandardResponse(
                status=422,
                data="query must contain either alias or command_id not both",
            ).into_response()

        if command_id is not None:
            await self.app.pool.execute("""
                DELETE FROM user_command_aliases
                WHERE user_id = $1 AND command_id = $2;
            """, user_id, command_id)
            return StandardResponse(
                status=200,
                data=f"removed all aliases for command: {command_id} if exists",
            )

        if alias is not None:
            await self.app.pool.execute("""
                DELETE FROM user_command_aliases
                WHERE user_id = $1 AND alias = $2;
            """, user_id, alias)
            return StandardResponse(
                status=200,
                data=f"removed alias: {alias} if exists",
            )

        return StandardResponse(
            status=422,
            data="missing one query out of alias or command_id",
        ).into_response()

    @router.endpoint(
        "/{user_id:int}/copy",
        endpoint_name="Copy User Aliases",
        methods=["POST"],
        response_model=AliasesResponse,
        tags=["Command User Aliases"]
    )
    async def copy_aliases(self, user_id: int, copy_to: int, target: AliasCopyTarget):
        """
        Copies a set of aliases from the given user to the target, the target
        can be either a guild or another user.
        """
        # todo auth

        if target == AliasCopyTarget.guild:
            results = await self.app.pool.fetch("""
                INSERT INTO guild_command_aliases (guild_id, command_id, alias) 
                SELECT $2, command_id, alias
                FROM user_command_aliases
                WHERE user_id = $1
                ON CONFLICT (guild_id, command_id, alias)
                DO NOTHING
                RETURNING alias, command_id;         
            """, user_id, copy_to)
        else:
            results = await self.app.pool.fetch("""
                INSERT INTO user_command_aliases (user_id, command_id, alias) 
                SELECT $2, command_id, alias
                FROM user_command_aliases
                WHERE user_id = $1
                ON CONFLICT (user_id, command_id, alias)
                DO NOTHING
                RETURNING alias, command_id;         
            """, user_id, copy_to)

        return AliasCopyResponse(
            status=200,
            data=list(map(dict, results))
        )


class CommandGuildAliasesBlueprint(router.Blueprint):
    __base_route__ = "/commands/aliases/guilds"

    def __init__(self, app: Backend):
        self.app = app

    @router.endpoint(
        "/{guild_id:int}",
        endpoint_name="Get Guild Aliases",
        methods=["GET"],
        response_model=AliasesResponse,
        tags=["Command Guild Aliases"]
    )
    async def get_aliases(self, guild_id: int):
        """ Gets the aliases for the given guild. """

        # todo auth

        results = await self.app.pool.fetch("""
            SELECT 
                guild_command_aliases.alias,
                guild_command_aliases.command_id, 
                commands.name,
                commands.category
            FROM guild_command_aliases
            INNER JOIN commands 
            ON commands.command_id = guild_command_aliases.command_id
            WHERE 
                guild_command_aliases.guild_id = $1;
        """, guild_id)

        return AliasesResponse(status=200, data=list(map(dict, results)))  # noqa

    @router.endpoint(
        "/{guild_id:int}/edit",
        endpoint_name="Add Guild Alias",
        methods=["POST"],
        response_model=StandardResponse,
        tags=["Command Guild Aliases"]
    )
    async def add_aliases(self, guild_id: int, payload: CommandAlias):
        """ Adds an alias for the given guild. """

        # todo auth

        fut = self.app.pool.execute("""
            INSERT INTO guild_command_aliases (guild_id, command_id, alias) 
            VALUES ($1, $2, $3);
        """, guild_id, payload.command_id, payload.alias)

        try:
            await fut
        except asyncpg.ForeignKeyViolationError:
            return StandardResponse(
                status=422,
                data=f"command with command id {payload.command_id} does not exist",
            ).into_response()

        return StandardResponse(
            status=200,
            data=f"alias added for command id {payload.command_id}",
        )

    @router.endpoint(
        "/{guild_id:int}/edit",
        endpoint_name="Remove Guild Alias",
        methods=["DELETE"],
        response_model=StandardResponse,
        tags=["Command Guild Aliases"],
    )
    async def remove_aliases(
        self,
        guild_id: int,
        alias: VarChar32 = None,
        command_id: VarChar32 = None,
    ):
        """ Removes an alias from the given guild. """

        # todo auth

        if command_id is not None and alias is not None:
            return StandardResponse(
                status=422,
                data="query must contain either alias or command_id not both",
            ).into_response()

        if command_id is not None:
            await self.app.pool.execute("""
                DELETE FROM guild_command_aliases
                WHERE guild_id = $1 AND command_id = $2;
            """, guild_id, command_id)
            return StandardResponse(
                status=200,
                data=f"removed all aliases for command: {command_id} if exists",
            )

        if alias is not None:
            await self.app.pool.execute("""
                DELETE FROM guild_command_aliases
                WHERE guild_id = $1 AND alias = $2;
            """, guild_id, alias)
            return StandardResponse(
                status=200,
                data=f"removed alias: {alias} if exists",
            )

        return StandardResponse(
            status=422,
            data="missing one query out of alias or command_id",
        ).into_response()

    @router.endpoint(
        "/{guild_id:int}/copy",
        endpoint_name="Copy Guild Aliases",
        methods=["POST"],
        response_model=AliasesResponse,
        tags=["Command Guild Aliases"]
    )
    async def copy_aliases(self, guild_id: int, copy_to: int, target: AliasCopyTarget):
        """
        Copies a set of aliases from the given guild to the target, the target
        can be either a user or another guild.
        """

        # todo auth

        if target == AliasCopyTarget.guild:
            results = await self.app.pool.fetch("""
                INSERT INTO guild_command_aliases (guild_id, command_id, alias) 
                SELECT $2, command_id, alias
                FROM guild_command_aliases
                WHERE guild_id = $1
                ON CONFLICT (guild_id, command_id, alias)
                DO NOTHING
                RETURNING alias;         
            """, guild_id, copy_to)
        else:
            results = await self.app.pool.fetch("""
                INSERT INTO user_command_aliases (user_id, command_id, alias) 
                SELECT $2, command_id, alias
                FROM guild_command_aliases
                WHERE guild_id = $1
                ON CONFLICT (user_id, command_id, alias)
                DO NOTHING
                RETURNING alias;         
            """, guild_id, copy_to)

        return AliasCopyResponse(
            status=200,
            data=list(map(dict, results))
        )


def setup(app):
    app.add_blueprint(CommandsBlueprint(app))
    app.add_blueprint(CommandUserAliasesBlueprint(app))
    app.add_blueprint(CommandGuildAliasesBlueprint(app))
