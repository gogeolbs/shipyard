import yaml

class Config():
	def __init__(self):
		try:
			f = open('config.yml')
		except Exception, e:
			f = open('commands/config.yml')

		try:
			defaults = yaml.safe_load(f)
			self.config = dict(defaults.items())
		except Exception, e:
			print 'Could not open file config.yml'
			self.config = dict()

	def __getitem__(self, key):
		try:
			value = self.config[key]
			return value
		except KeyError as err:
			print 'KeyError', err
			return None
