import enum
import datetime
import argparse

import models
from tortoise import Tortoise
from nicegui import app, ui

async def init_db() -> None:
    await Tortoise.init(db_url="sqlite://db.sqlite3", modules={"models": ["models"]})
    await Tortoise.generate_schemas()

async def close_db() -> None:
    await Tortoise.close_connections()

app.on_startup(init_db)
app.on_shutdown(close_db)

def add_create_event():
    date = ui.date()
    async def create():
        if len([e for e in await models.Event.filter(date=date.value)]) > 0:
            ui.notify("date already has an event", type="negative")
        else:
            event = await models.Event.create(date=date.value)
            async for participant in models.Participant.filter(add_per_default=True):
                await models.Participation.create(event=event, participant=participant, added_medium="auto", showed_up = ShowedUp.unknown, added_time=datetime.datetime.now())
            ui.navigate.reload()
    ui.button("Add", on_click=create)

@ui.refreshable
async def all_participant_list():
    participants: list[models.Participant] = await models.Participant.all()
    
    for p in participants:
        ui.input("nickname", on_change=p.save).bind_value(p, "nickname")
        ui.input("realname", on_change=p.save).bind_value(p, "realname")
        ui.checkbox("add", on_change=p.save).bind_value(p, "add_per_default")
        ui.input("note", on_change=p.save).bind_value(p, "note")



async def add_participant_list(participants: list[models.Participant]):
    with ui.grid(columns=4):
        ui.label("nickname")
        ui.label("realname")
        ui.label("add default")
        ui.label("note")

        await all_participant_list()

        new = models.Participant()
        ui.input("nickname").bind_value(new, "nickname")
        ui.input("realname").bind_value(new, "realname")
        async def save():
            await new.save()
            all_participant_list.refresh()
        ui.button("add", on_click=save)
        ui.label("")

def to_single_string(p: models.Participant):
    return f"{p.nickname}/{p.realname}"

class ShowedUp(enum.IntEnum):
    unknown = enum.auto()
    showed = enum.auto()
    noshow = enum.auto()

@ui.refreshable
async def event_participant_list(event_date: str):
    event = await models.Event.get(date=event_date)

    with ui.grid(columns="2fr 1fr 1fr 1fr 1fr").classes("gap-0 w-full"):
        ui.label("name") 
        ui.label("cancel")
        ui.label("showed")
        ui.label("medium")
        ui.label("note")
        async for participation in event.participations:
            participant = await participation.participant
            ui.label(to_single_string(participant))
            ui.checkbox("", on_change=participation.save).bind_value(participation, "cancelled")
            ui.toggle({ShowedUp.unknown: "?", ShowedUp.showed: "Y", ShowedUp.noshow: "N"}, on_change=participation.save).bind_value(participation, "showed_up")
            ui.label(participation.added_medium)
            ui.label(participant.note)


async def add_event_participant_list(event: models.Event, all_participants: list[models.Participant]):
    event_participants: list[models.Participant] = [await p.participant async for p in event.participations]

    await event_participant_list(event.date)

    with ui.row():
        options = {to_single_string(p): p for p in all_participants if not p in event_participants}
        select = ui.select(options=list(options.keys()), with_input=True)
        async def add_participant():
            p = options[select.value]
            await models.Participation.create(event=event, participant=p, added_medium="", showed_up = ShowedUp.unknown, added_time=datetime.datetime.now())
            event_participant_list.refresh()
        ui.button("Add", on_click=add_participant)


@ui.page("/")
async def index():
    events: list[models.Event] = await models.Event.all()
    participants: list[models.Participant] = await models.Participant.all()
    with ui.tabs() as tabs:
        for event in sorted([e for e in events if e.date >= datetime.date.today()], key=lambda x: x.date):
            ui.tab(event.date, icon="event")
        ui.tab("add", label="add event", icon="add")
        ui.tab("participants", label="participants", icon="people")
        for event in sorted([e for e in events if e.date < datetime.date.today()], key=lambda x: x.date, reverse=True):
            ui.tab(event.date, icon="event")
    with ui.tab_panels(tabs).classes("w-full"):
        with ui.tab_panel("add"):
            add_create_event()
        with ui.tab_panel("participants"):
            await add_participant_list(participants)
        for event in events:
            with ui.tab_panel(event.date):
                await add_event_participant_list(event, participants)

ui.run()

