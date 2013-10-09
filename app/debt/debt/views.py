from django.shortcuts import render
from debt.models import Debt, Person, Instance
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

class DotExpandedDict(dict):
    """
    A special dictionary constructor that takes a dictionary in which the keys
    may contain dots to specify inner dictionaries. It's confusing, but this
    example should make sense.

    >>> d = DotExpandedDict({'person.1.firstname': ['Simon'], \
            'person.1.lastname': ['Willison'], \
            'person.2.firstname': ['Adrian'], \
            'person.2.lastname': ['Holovaty']})
    >>> d
    {'person': {'1': {'lastname': ['Willison'], 'firstname': ['Simon']}, '2': {'lastname': ['Holovaty'], 'firstname': ['Adrian']}}}
    >>> d['person']
    {'1': {'lastname': ['Willison'], 'firstname': ['Simon']}, '2': {'lastname': ['Holovaty'], 'firstname': ['Adrian']}}
    >>> d['person']['1']
    {'lastname': ['Willison'], 'firstname': ['Simon']}

    # Gotcha: Results are unpredictable if the dots are "uneven":
    >>> DotExpandedDict({'c.1': 2, 'c.2': 3, 'c': 1})
    {'c': 1}
    """
    def __init__(self, key_to_list_mapping):
        for k, v in key_to_list_mapping.items():
            current = self
            bits = k.split('.')
            for bit in bits[:-1]:
                current = current.setdefault(bit, {})
            # Now assign value to current position
            try:
                current[bits[-1]] = v
            except TypeError: # Special-case if current isn't a dict.
                current = {bits[-1]: v}

# Emulates the spreadsheet's entries view
def entries(request, instance_id):
  instance = Instance.objects.get(id=instance_id)
  state = instance.latest_state()
  entries = state.debts.order_by('date')
  context = {'entries': entries, 'instance': instance }
  return render(request, 'debt/entries.html', context)

def delete_state(request, instance_id, state_id):
  instance = Instance.objects.get(id=instance_id)
  latest = instance.latest_state()

  try:
    if latest.id == int(state_id):
      for person in latest.people.all():
        if len(person.state_set.all()) == 1:
          person.delete()
      for debt in latest.debts.all():
        if len(debt.state_set.all()) == 1:
          for subdebt in debt.subdebt_set.all():
            subdebt.delete()
          debt.delete()
      latest.delete()
  except Exception as e:
    print e
    return HttpResponseRedirect(reverse('changes', args=(instance.id,)))
  else:
    return HttpResponseRedirect(reverse('changes', args=(instance.id,)))

def add_person(request, instance_id):
  instance = Instance.objects.get(id=instance_id)
  latest = instance.latest_state()

  try:
    try:
      plusone = latest.people.get(id=int(request.POST['plusone']))
    except Person.DoesNotExist:
      plusone = None
    name = request.POST['name'].strip()
    nstate = latest.clone("Adding new person: " + str(name))
    person = nstate.people.create(name=name,plusone=plusone)

  except (KeyError, Person.DoesNotExist):
    people = instance.latest_state().people.order_by('name')
    context = {'instance': instance, 'people': people}
    return render(request, 'debt/add_person.html', context)
  else:
    return HttpResponseRedirect(reverse('detailed', args=(instance.id,)))

def add_entry(request, instance_id):
  instance = Instance.objects.get(id=instance_id)
  latest = instance.latest_state()

  try:
    debtee = latest.people.get(id=request.POST['debtee'])
    debtors_u = request.POST.getlist('debtor')
    reason = request.POST['reason'].strip()
    debtors = latest.people.filter(id__in=debtors_u)
    cost =  int( (float(request.POST['total_cost']) * 100.0 ) / len(debtors))
    if len(debtors) != len(debtors_u):
      raise Person.DoesNotExist(str(debtors_u) + ' - ' + str(debtors))

    nstate = latest.clone("Adding new debt for: " + str(reason))

    debt = nstate.debts.create(what=reason,debtee=debtee)

    for debtor in debtors:
      debt.subdebt_set.create(cost=cost,debtor=debtor)

  except (KeyError, Person.DoesNotExist):
    people = instance.latest_state().people.order_by('name')
    context = {'instance': instance, 'people': people}
    return render(request, 'debt/add.html', context)
  else:
    return HttpResponseRedirect(reverse('entries', args=(instance.id,)))

def add_entry_advanced(request, instance_id):
  instance = Instance.objects.get(id=instance_id)
  latest = instance.latest_state()

  try:
    debtee = latest.people.get(id=request.POST['debtee'])
    debtors = DotExpandedDict(request.POST)['debtor']

    reason = request.POST['reason'].strip()

    nstate = latest.clone("Adding new debt for: " + str(reason))

    debt = nstate.debts.create(what=reason,debtee=debtee)

    for debtor in debtors:
      if int(debtors[debtor]) > 0:
        dperson = latest.people.get(id=debtor)
        cost =  int(float(debtors[debtor]) * 100.0)
        debt.subdebt_set.create(cost=cost,debtor=dperson)

  except (KeyError, Person.DoesNotExist):
    people = instance.latest_state().people.order_by('name')
    context = {'instance': instance, 'people': people}
    return render(request, 'debt/add_advanced.html', context)
  else:
    return HttpResponseRedirect(reverse('entries', args=(instance.id,)))

def changes(request, instance_id):
  instance = Instance.objects.get(id=instance_id)
  states = instance.state_set.order_by('date')
  context = {'states': states, 'instance': instance }
  return render(request, 'debt/states.html', context)

class Summary:
  def __init__(self, name):
    self.name = name
    self.owes = 0
    self.paid = 0
  def name(self):
    return self.name
  def paid_gbp(self):
    return "%.2f" % (self.paid / 100.0) 
  def owes_gbp(self):
    return "%.2f" % (self.owes / 100.0) 
  def add_debt(self, amount):
    self.owes += amount
  def add_asset(self, amount):
    self.paid += amount
  def balance(self):
    return self.paid - self.owes
  def balance_gbp(self):
    return "%.2f" % (self.balance() / 100.0) 

def find_top_plusone(f, people, cache):
  found = []
  if f in cache:
    return cache[f]
  k = f
  while k not in found and people[k]:
    found.append(k)
    k = people[k]
  cache[f] = k
  return k

def summary(request, instance_id):

  cache = {}
  data = {}
  people = {}

  instance = Instance.objects.get(id=instance_id)

  state = instance.latest_state()

  # Add all the people

  for person in state.people.filter(plusone_id=None):
    data[person.id] = Summary(person.name)

  for person in state.people.all():
    people[person.id] = person.plusone_id

  print data

  # Add all the debts

  for debt in state.debts.all():
    total = 0
    for subdebt in debt.subdebt_set.all():
       data[find_top_plusone(subdebt.debtor.id, people, cache)].add_debt(subdebt.cost)
       total += subdebt.cost
    data[find_top_plusone(debt.debtee.id, people, cache)].add_asset(total)

  sort = sorted(data.values(), key=lambda summary: summary.balance())

  context = {'data': sort, 'instance': instance, 'title': 'Summary' }

  return render(request, 'debt/summary.html', context)

# Emulates the spreadsheet's summary view
def detailed(request, instance_id):

  data = {}

  instance = Instance.objects.get(id=instance_id)

  state = instance.latest_state()

  # Add all the people

  for person in state.people.all():
    data[person.id] = Summary(person.name)

  # Add all the debts

  for debt in state.debts.all():
    total = 0
    for subdebt in debt.subdebt_set.all():
       data[subdebt.debtor.id].add_debt(subdebt.cost)
       total += subdebt.cost
    data[debt.debtee.id].add_asset(total)

  sort = sorted(data.values(), key=lambda summary: summary.balance())

  context = {'data': sort, 'instance': instance, 'title': 'Detailed' }

  return render(request, 'debt/summary.html', context)

