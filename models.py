from tortoise import fields, models

class Participant(models.Model):
    id = fields.IntField(primary_key=True)
    realname = fields.CharField(max_length=255, default="?")
    nickname = fields.CharField(max_length=255, default="?")
    add_per_default = fields.BooleanField(default=False)
    note = fields.CharField(max_length=255, default="")


class Event(models.Model):
    id = fields.IntField(primary_key=True)
    date = fields.DateField()

class Participation(models.Model):
    id = fields.IntField(primary_key=True)
    event = fields.ForeignKeyField("models.Event", related_name="participations")
    participant = fields.ForeignKeyField("models.Participant", related_name="participations")
    added_time = fields.DateField(auto_now_add=True)
    added_medium = fields.CharField(max_length=32)
    cancelled = fields.BooleanField(default=False)
    showed_up = fields.IntField()

