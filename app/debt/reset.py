# vim: set fileencoding=utf-8

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "debt.settings")

from datetime import datetime
from debt.models import Instance, State, Person, SubDebt, Debt
from reset_local import name

instance = Instance.objects.get(id=1)

def clear_all():
  instance.state_set.all().delete()
#  for person in Person.objects.all():
#    if len(person.state_set) == 0:
#      person.delete()
  for debt in Debt.objects.all():
    if len(debt.state_set.all()) == 0:
      debt.subdebt_set.all().delete()
      debt.delete()

def parse_file():

  data = []
  entry = None

  nmap = [
    'date',
    'what',
    'cost',
    'who',
    'owes'
  ]

  with open('ss_of_debt.txt') as f:
    n = 0
    for line in f:
      if n == 0:
        entry = {}
      entry[nmap[n]] = line.strip().strip('£')
      n += 1
      if n == len(nmap):
        n = 0
        data.append(entry)
        entry = None

  if entry:
    data.append(entry)

  return data

def add_objects(data):

  state = instance.state_set.create(reason='Initial import')

  for entry in data:
    who = Person.objects.filter(name=name(entry['who']))
    if len(who) != 1:
      raise Exception('Unknown person: ' + str(entry['who']) + ' got: ' + str(who))

    person = who[0]

    state.people.add(person)

    owes = [name(x.strip()) for x in entry['owes'].split(',')]
    to = Person.objects.filter(name__in=owes)

    if len(owes) != len(to):
      raise Exception('Unable to resolve all the people: ' + str(entry['owes']) + ' got: ' + str(to))

    for toi in to:
      state.people.add(toi)

    cost = int((float(entry['cost']) * 100) / len(to))

    date = datetime.strptime(entry['date'], "%d/%m/%Y %H:%M:%S",)

    # Create the Debt object

    ndebt = person.debt_set.create(what=entry['what'], date=date)

    state.debts.add(ndebt)

    # Create the SubDebt objects

    for ower in to:
      ndebt.subdebt_set.create(cost=cost, debtor=ower)

if __name__ == "__main__":
  clear_all()
  add_objects(parse_file())
