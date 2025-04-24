import enum
import datetime
import argparse
from typing import Optional
from uuid import UUID, uuid4
import json

from pydantic import BaseModel, Field, computed_field
from nicegui import app, ui

from backup_save import BackupSave

class Test(BaseModel):
    internal_value: bool = Field(default=False, exclude=True)

    @computed_field
    @property
    def foo(self)-> bool:
        return self.internal_value
    
    @foo.setter
    def foo(self, value: bool):
        self.internal_value = value
        print(f"called setter with {value}")

t=Test(foo=False)
print("instantiated")
t.foo = True
print(t.model_dump_json())


class ShowedUp(enum.IntEnum):
    unknown = enum.auto()
    showed = enum.auto()
    noshow = enum.auto()



class Participant(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
    names: dict[str, str]
    add_default: bool = False
    note: str = ""

    reservations: "Reservation" = Field(default_factory=list, exclude=True)

    def all_names(self) -> str:
        return "/".join(self.names.values())

class Event(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
    date: datetime.date
    
    reservations: "Reservation" = Field(default_factory=list, exclude=True)

    statistics: dict = Field(default_factory=dict, exclude=True)

    def calculate_statistics(self) -> dict:
        total = expected = cancelled = shows = noshows = unknown = 0

        for r in self.reservations:
            total += 1
            if r.cancelled:
                cancelled += 1
            else:
                expected += 1
                if r.showed_up == ShowedUp.showed:
                    shows += 1
                elif r.showed_up == ShowedUp.noshow:
                    noshows += 1
                else:
                    unknown += 1
        self.statistics.update({"total": total, "expected": expected, "cancelled": cancelled, "shows": shows, "noshows": noshows, "unknown": unknown})




class Reservation(BaseModel):
    uid: UUID = Field(default_factory=uuid4)
    added_time: datetime.datetime = Field(default_factory=datetime.datetime.now)
    source: Optional[str]

    _cancelled: bool = False
    @computed_field
    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @cancelled.setter
    def cancelled(self, value: bool):
        self._cancelled = value
        self.event.calculate_statistics()

    

    _showed_up: ShowedUp = ShowedUp.unknown
    @computed_field
    @property
    def showed_up(self) -> ShowedUp:
        return self._showed_up

    @showed_up.setter
    def showed_up(self, value: ShowedUp):
        self._showed_up = value
        self.event.calculate_statistics()

    note: str = ""

    event_uid: UUID
    participant_uid: UUID

    event: Optional[Event] = Field(exclude=True, default=None)
    participant: Optional[Participant] = Field(exclude=True, default=None)
    
    @staticmethod
    def make(event: Event, participant: Participant, source: str="TODO", **kwargs):
        r = Reservation(event_uid = event.uid, participant_uid=participant.uid, event=event, participant=participant, source=source, **kwargs)
        event.reservations.append(r)
        participant.reservations.append(r)
        return r


class Model(BaseModel):
    sources: list[str] = list()
    known_names: list[str] = list()
    participants: list[Participant] = list()
    events: list[Event] = list()
    reservations: list[Reservation] = list()

    def object_by_uid(self, objects, uid: UUID):
        for o in objects:
            if o.uid == uid:
                return o
        else:
            raise KeyError(uid)

    def event_by_uid(self, uid: UUID) -> Event:
        return self.object_by_uid(self.events, uid)

    def participant_by_uid(self, uid: UUID) -> Participant:
        return self.object_by_uid(self.participants, uid)

    def reservation_by_uid(self, uid: UUID) -> Reservation:
        return self.object_by_uid(self.reservations, uid)
    
    def event_by_date(self, date: datetime.date|str):
        if isinstance(date, str):
            date = datetime.date.fromisoformat(date)
        for e in self.events:
            if e.date == date:
                return e
        else:
            raise KeyError(date)

    def get_reservation(self, event: Event, participant: Participant):
        for r in self.reservations:
            print(self.reservations)
            if r.event == event and r.participant == participant:
                return r
        else:
            raise KeyError()

model = Model()

def load(data_store):
    global model
    try:
        model = data_store.load()
    except RuntimeError:
        print("unable to load json")
        model = Model()
        add_example_data()

    connect()

def add_example_data():
    model.sources = ["PM", "FL"]
    model.known_names = ["real", "FL"]
    e = Event(date="2025-01-01")
    model.events.append(e)
    p = Participant(names={"real": "Kurt", "FL": "somebody"})
    model.participants.append(p)
    model.participants.append(Participant(names={"real": "Max", "FL": "whatever"}))
    r = Reservation(event_uid=e.uid, participant_uid=p.uid, source="FL")
    model.reservations.append(r)

def connect():
    for reservation in model.reservations:
        reservation.event = model.event_by_uid(reservation.event_uid)
        reservation.participant = model.participant_by_uid(reservation.participant_uid)
        reservation.event.reservations.append(reservation)
        reservation.participant.reservations.append(reservation)


def save(data_store):
    data_store.save(model.model_dump_json(indent=2))

def event_statistics(event: Event):
    def make_element(icon, color, data_field):
        ui.button(icon=icon, color=color).bind_text(event.statistics, data_field).set_enabled(False)
        #ui.chip(icon=icon, color=color).bind_text(event.statistics, data_field)

    with ui.row():
        make_element("list", "blue", "expected")
        make_element("done", "green", "shows")
        make_element("error", "red", "noshows")
        make_element("cancel", "grey", "cancelled")
        make_element("question_mark", "grey", "unknown")


@ui.refreshable
def reservation_list(event: Event):
    with ui.grid(columns="2fr 1fr 1fr 1fr 1fr 1fr").classes("gap-0 w-full"):
        ui.label("name") 
        ui.label("cancel")
        ui.label("showed")
        ui.label("medium")
        ui.label("note")
        ui.label("p. note")
        for reservation in event.reservations:
            participant = reservation.participant
            ui.label(participant.all_names())
            ui.checkbox("").bind_value(reservation, "cancelled")
            #ui.toggle({ShowedUp.unknown: "?", ShowedUp.showed: "Y", ShowedUp.noshow: "N"}, on_change=event.calculate_statistics()).bind_value(reservation, "showed_up")
            ui.select({ShowedUp.unknown: "?", ShowedUp.showed: "Y", ShowedUp.noshow: "N"}, on_change=event.calculate_statistics()).bind_value(reservation, "showed_up")
            ui.label(reservation.source)
            ui.input().bind_value(reservation, "note")
            ui.input().bind_value(participant, "note")

def add_reservation(event: Event):
    with ui.row():
        event_participants = [r.participant for r in event.reservations]
        remaining_participants = [p for p in model.participants if not p in event_participants]
        options = {p.all_names(): p for p in remaining_participants}
        select = ui.select(options=list(options.keys()), with_input=True)
        source_select = ui.select(options=model.sources, value=model.sources[0])
        def add_participant():
            p = options[select.value]
            try:
                model.get_reservation(event=event, participant=p)
            except KeyError:
                r = Reservation.make(event=event, participant=p, source=source_select.value)
                model.reservations.append(r)
                reservation_list.refresh()
            else:
                ui.notify("participant already added", type="negative")

        ui.button("Add", on_click=add_participant)

def get_event_dates():
    dates_future = sorted((event.date for event in model.events if event.date + datetime.timedelta(days=2) > datetime.date.today()))
    dates_past = reversed(sorted((event.date for event in model.events if event.date + datetime.timedelta(days=2) <= datetime.date.today())))
    return dates_future, dates_past

def navbar(title: str):
    with ui.header().classes('items-center justify-between'):
        ui.label(title)

        with ui.row():
            ui.button(on_click=lambda: ui.navigate.to("/newevent"), icon='add')
            ui.button(on_click=lambda: ui.navigate.to("/participants"), icon='people')
            ui.button(on_click=lambda: ui.navigate.to("/settings"), icon='settings')

            with ui.button(icon="event"):
                with ui.menu() as menu:
                    dates_future, dates_past = get_event_dates()
                    for date in dates_future:
                        ui.menu_item(date, lambda: ui.navigate.to(f"/event/{date}"))
                    ui.separator()
                    for date in dates_past:
                        ui.menu_item(date, lambda: ui.navigate.to(f"/event/{date}"))

@ui.page("/event/{date}")
def event_page(date: str):
    navbar(date)
    try:
        event = model.event_by_date(date)
    except KeyError:
        ui.label("no event on this date")
    else:
        event_statistics(event)
        reservation_list(event)
        add_reservation(event)


@ui.page("/newevent")
def newevent():
    navbar("new event")
    date = ui.date()
    def create():
        d = date.value
        try:
            model.event_by_date(d)
            ui.notify("date already has an event", type="negative")
        except KeyError:
            e = Event(date=d)
            model.events.append(e)
            for p in model.participants:
                if p.add_default:
                    model.reservations.append(Reservation.make(event=e, participant=p))
            ui.navigate.to(f"/event/{d}")
    ui.button("Add", on_click=create)

@ui.refreshable
def participant_list():
    for p in model.participants:
        for name in model.known_names:
            ui.input(name).bind_value(p.names, name)
        ui.checkbox("add").bind_value(p, "add_default")
        ui.input("note").bind_value(p, "note")


def add_participant():
    name_inputs = {}
    for name in model.known_names:
        name_inputs[name] = ui.input(name)
    def save():
        names = {k: v.value for k, v in name_inputs.items()}
        if len([n for n in names.values() if n]) == 0:
            ui.notify("fill out at least one name", type="negative")
        else:
            p = Participant(names=names)
            model.participants.append(p)
            for v in name_inputs.values():
                v.value = ""
            participant_list.refresh()
    ui.button("add", on_click=save)
    ui.label("")

 

@ui.page("/participants")
def participants():
    navbar("participant list")
    with ui.grid(columns=2+len(model.known_names)):
        for name in model.known_names:
            ui.label(name)
        ui.label("add default")
        ui.label("note")

        participant_list()
        add_participant()


@ui.page("/settings")
def settings():
    pass

                 
@ui.page("/")
def index():
    future_events, _ = get_event_dates()
    if len(future_events) > 0:
        ui.navigate.to(f"/event/{future_events[0]}")
    else:
        navbar("homepage")
        ui.label("no future events planned")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default=None)
    parser.add_argument("--folder", type=str, default="data", required=False)
    return parser.parse_args()


def main():
    args = parse_args()
    data_store = BackupSave(folder=args.folder, basename="data.json", validator=Model.model_validate_json)
    load(data_store)
    ui.timer(10.0, lambda: save(data_store))
    app.on_shutdown(lambda: save(data_store))
    ui.run(host=args.host)

main()

