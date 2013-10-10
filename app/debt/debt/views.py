from django.shortcuts import render
from debt.models import Debt, Person, Instance
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from functools import cmp_to_key

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
    return HttpResponseRedirect(reverse('individual', args=(instance.id,)))

def add_entry(request, instance_id):
  instance = Instance.objects.get(id=instance_id)
  latest = instance.latest_state()

  try:
    debtee = latest.people.get(id=request.POST['debtee'])
    debtors_u = request.POST.getlist('debtor')
    reason = request.POST['reason'].strip()
    debtors = latest.people.filter(id__in=debtors_u).filter(retired=False)
    cost =  int( (float(request.POST['total_cost']) * 100.0 ) / len(debtors))
    if len(debtors) != len(debtors_u):
      raise Person.DoesNotExist(str(debtors_u) + ' - ' + str(debtors))

    nstate = latest.clone("Adding new debt for: " + str(reason))

    debt = nstate.debts.create(what=reason,debtee=debtee)

    for debtor in debtors:
      debt.subdebt_set.create(cost=cost,debtor=debtor)

  except (KeyError, Person.DoesNotExist):
    people = latest.people.filter(retired=False).order_by('name')
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
    people = latest.people.filter(retired=False).order_by('name')
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
  def __init__(self, id, name, plusone):
    self._depth = None
    self.id = id
    self.name = name
    self.owes = 0
    self.paid = 0
    self.parent = None
    self.plusone = plusone
    self.subs = []
  def has_sub(self, sub):
    for s in self.subs:
      if s.id == sub.id or s.has_sub(sub):
        return True
    return False
  def add_sub(self, sub):
    self.subs.append(sub)
  def add_parent(self, parent):
    self.parent = parent
  def name(self):
    return self.name
  def paid_gbp(self):
    return "%.2f" % (self.paid / 100.0) 
  def owes_gbp(self):
    return "%.2f" % (self.owes / 100.0) 
  def add_debt(self, amount, mode):
    self.owes += amount
    if mode != 'individual' and self.parent:
      self.parent.add_debt(amount, mode)
  def add_asset(self, amount, mode):
    self.paid += amount
    if mode != 'individual' and self.parent:
      self.parent.add_asset(amount, mode)
  def balance(self):
    return self.paid - self.owes
  def balance_gbp(self):
    return "%.2f" % (self.balance() / 100.0) 
  def depth(self):
    if self._depth:
      return self._depth
    if self.parent:
      self._depth = self.parent.depth() + 1
    else:
      self._depth = 0
    return self._depth
  def indent(self):
    return range(self.depth())
  

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
  return balances(request, instance_id, 'summary')

def detailed(request, instance_id):
  return balances(request, instance_id, 'detailed')

def individual(request, instance_id):
  return balances(request, instance_id, 'individual')

def detail_sort(x,y):
  if x.id == y.id:
    return 0
  if x.has_sub(y):
    return -1
  if y.has_sub(x):
    return 1
  if x.parent and y.parent and x.parent.id != y.parent.id:
    return detail_sort(x.parent, y)
  elif x.parent:
    return detail_sort(x.parent, y)
  elif y.parent:
    return detail_sort(x, y.parent)
  return x.balance() - y.balance()

def balances(request, instance_id, mode):
  cache = {}

  people = {}
  data = {}

  instance = Instance.objects.get(id=instance_id)

  state = instance.latest_state()

  # Add all the people

  for person in state.people.all():
    summary = Summary(person.id,person.name,person.plusone_id)
    if (not person.retired) and (person.plusone == None or mode != 'summary'):
      data[person.id] = summary
    people[person.id] = summary

  for person in people:
    if people[person].plusone and people[person].plusone in data:
      people[people[person].plusone].add_sub(people[person])
      people[person].add_parent(data[people[person].plusone])

  max_depth = 0

  for person in people:
    i = people[person].depth()
    if i > max_depth:
      max_depth = i

  # Add all the debts

  for debt in state.debts.all():
    total = 0
    for subdebt in debt.subdebt_set.all():
       people[subdebt.debtor.id].add_debt(subdebt.cost, mode)
       total += subdebt.cost
    people[debt.debtee.id].add_asset(total, mode)

  if mode == 'detailed':
    sort = sorted(data.values(), key=cmp_to_key(detail_sort))
  else:
    sort = sorted(data.values(), key=lambda summary: summary.balance())

  context = {'data': sort, 'instance': instance, 'title': mode.title(), 'mode': mode, 'max_indent': max_depth}

  template = 'debt/summary.html'

  if mode == 'detailed':
    template = 'debt/detailed.html'

  return render(request, 'debt/summary.html', context)

