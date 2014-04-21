# vim: set fileencoding=utf-8

from django.db import models
from datetime import datetime

# Represents an instance of the debt tracks
class Instance(models.Model):

  # Name of the instance
  name = models.CharField(max_length=200)

  # Latest state
  def latest_state(self):
    try:
      return self.state_set.order_by('-date')[0]
    except IndexError, e:
      raise State.DoesNotExist(e)

  def __unicode__(self):
    return self.name

# Represents a person to whom money can be owed
class Person(models.Model):

  # Name of the person
  name = models.CharField(max_length=200)

  # Email of the person
  email = models.CharField(max_length=200)

  # Plus one of this person
  plusone = models.ForeignKey('self', blank=True, null=True)

  # Are they retired?
  retired = models.BooleanField(default=False)

  def __unicode__(self):
    return self.name

# Represents a debt in the system
class Debt(models.Model):

  # What caused the debt
  what = models.CharField(max_length=200)

  # When was the debt incurred
  date = models.DateTimeField('date entered', default=datetime.now, blank=True)

  # Who is owed the debt (i.e. who paid)
  debtee = models.ForeignKey(Person)

  def cost(self):
    return sum([x.cost for x in self.subdebt_set.all()])

  def cost_gbp(self):
    return "%.2f" % (self.cost() / 100.0)

  def debtors(self):
    return [x.debtor.name for x in self.subdebt_set.all()]

  def __unicode__(self):
    return self.what + " on " + str(self.date)

# Represents the money that a person may be owed
class SubDebt(models.Model):

  # Debt to which this is part of
  debt = models.ForeignKey(Debt)

  # How much is the debt (in pence)
  cost = models.IntegerField()

  # Who owes the debt (i.e. who else was there)
  debtor = models.ForeignKey(Person)

  def __unicode__(self):
    return str(self.debtor) + " owes " + ("%.2f" % (self.cost/100.0)) + " for " + str(self.debt)

# Represents the state of the system
class State(models.Model):

  # Date state was first present
  date = models.DateTimeField('date actioned', default=datetime.now, blank=True)

  # The people the system knows about at this state
  people = models.ManyToManyField(Person)

  # The debts the system knows about at this state
  debts = models.ManyToManyField(Debt)

  # Reason
  reason = models.CharField(max_length=200, blank=False)

  # The parent state(s)
  parent = models.ManyToManyField('self', blank=True, null=True)

  # The parent instance
  instance = models.ForeignKey(Instance)

  # Return a clone of this state, setting the parent and reason
  def clone(self, reason):
    nstate = State(instance=self.instance, reason=reason)
    nstate.save()
    nstate.parent.add(self)
    for debt in self.debts.all():
      nstate.debts.add(debt)
    for person in self.people.all():
      nstate.people.add(person)
    return nstate

  def __unicode__(self):
    return self.reason

