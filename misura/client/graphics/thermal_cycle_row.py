from misura.canon.csutil import next_point

class ThermalCycleRow():
	def update_row(self, dat, irow, mode):
		if isinstance(dat[irow][1],basestring):
			return dat[irow]
		t, T, R, D = dat[irow]
		pt0, ent0 = next_point(dat, irow - 1, -1)
		if ent0 is False:
			return dat[irow]
		t0, T0, R0, D0=ent0
		if mode=='points':
			D=(t-t0)
			if D == 0: R = 0
			else:
				R = (T - T0)/D
		elif mode == 'ramp':
			if R == 0: D = 0
			else:
				D = (T - T0)/R
			t = t0 + D
		elif mode == 'dwell':
			if D == 0: R = 0
			else:
				R = (T - T0)/D
			t = t0 + D
		if D < 0 or t < t0:
			return [t0 + 1, T0, 0, 1]
		else:
			return [t, T, R, D]
