import time

import frappe
from frappe import _
from redis.exceptions import WatchError
from uuid_utils import uuid7


def acquire_lock(lockname: str, acquire_timeout: int, lock_timeout: int) -> str | None:
	"""
	Acquire a distributed lock using Redis.
	Returns a unique identifier for the lock if acquired, else None.

	:param lockname: Unique lock name
	:param acquire_timeout: How long to wait for lock (0 = no wait)
	:param lock_timeout: TTL for lock in seconds
	"""

	if lock_timeout <= 0:
		frappe.throw(_("Lock timeout must be greater than 0 seconds."))

	cache = frappe.cache()
	identifier = str(uuid7())
	lock_key = f"lock:{lockname}"

	if acquire_timeout == 0:
		return identifier if cache.set(lock_key, identifier, ex=lock_timeout, nx=True) else None

	end = time.time() + acquire_timeout
	while time.time() < end:
		if cache.set(lock_key, identifier, ex=lock_timeout, nx=True):
			return identifier
		time.sleep(0.001)

	return None


def release_lock(lockname: str, identifier: str) -> bool:
	"""
	Release the lock only if it is held by the caller.
	"""

	cache = frappe.cache()
	lock_key = f"lock:{lockname}"
	pipe = cache.pipeline(True)

	while True:
		try:
			pipe.watch(lock_key)
			value = pipe.get(lock_key)
			if value and value.decode() == identifier:
				pipe.multi()
				pipe.delete(lock_key)
				pipe.execute()
				return True

			pipe.unwatch()
			break
		except WatchError:
			continue

	return False
