from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools,api 
from dateutil import relativedelta
import datetime
import itertools 	

class mmr_sales(osv.osv):
	_name = "mmr.sales"
	_description = "Modul sales untuk PT. MMR."
	_rec_name = "nama"
	
	# Hitung pencapaian sales otomatis
	def _isi_pencapaian(self, cr, uid, ids, field_name, arg, context):
		res = {}
		for sales in self.browse(cr,uid,ids):
			# Hitung Total Hutang, Cari Seluruh PO dengan supplier ini
			# Ambil seluruh fakturnya, jumlahkan nettonya
			total = 0
			for semuapo in sales.listpopenjualan:
				for semuafaktur in semuapo.penjualanfaktur:
					if datetime.datetime.strptime(semuafaktur.tanggalterbit,'%Y-%m-%d').strftime("%m") == datetime.datetime.today().strftime("%m"):
						total+=semuafaktur.hppembelian
			penjualanreturClass = self.pool.get("mmr.penjualanretur")
			hasilsearch = penjualanreturClass.search(cr,uid,[])
			for semuapenjualanretur in hasilsearch:
				penjualanrturobj = penjualanreturClass.browse(cr,uid,semuapenjualanretur)
				if datetime.datetime.strptime(penjualanrturobj.tanggalterbit,'%Y-%m-%d').strftime("%m") == datetime.datetime.today().strftime("%m") and penjualanrturobj.idpopenjualan.sales == sales:
					total-=penjualanrturobj.hppembelian
			res[sales.id] = total
			
		return res
	
	_columns = {
		'userid': fields.many2one("res.users", "User ID", required=True),
		'nama' : fields.char("Alias", size=3, required=True),
		'listrayon' : fields.many2many("mmr.rayon","rayon_sales","listrayon","listsales", "Rayon"),
		'listpopenjualan' : fields.one2many("mmr.penjualanpo","sales","List Penjualan PO"),
		'pencapaian': fields.function(_isi_pencapaian,string="Pencapaian Bulan Ini",method=True,type="float", digits=(12,2)),
		'laporansales' : fields.one2many("mmr.laporansales","sales","Laporan"),
		'notes' : fields.text("Notes"),
	}	
	
	_sql_constraints = [
        ('name_uniq', 'unique(userid)', 'User Telah Menjadi Sales!')
    ]
	
mmr_sales()

class mmr_laporansales(osv.osv):
	_name = "mmr.laporansales"
	_description = "Modul laporan sales untuk PT. MMR."
	
	# Apabila sales yang mengisi laporan, tidak dapat merubah nama sales
	def onchange_sales(self,cr,uid,ids,sales,context=None):
		hasil ={}
		grupClass = self.pool.get("res.groups")
		grupobj = grupClass.search(cr,uid,[('name','=','Admin')])
		userClass = self.pool.get("res.users")
		grupditemukan = False
		for semuagrup in userClass.browse(cr,uid,uid).groups_id:
			if semuagrup.id == grupobj[0]:
				grupditemukan = True
		if grupditemukan and sales:
			hasil['sales'] = sales
			return {'value': hasil}	
		salesClass = self.pool.get("mmr.sales")
		salesobj = salesClass.search(cr,uid,[('userid','=',uid)])
		if salesobj:
			hasil['sales'] = salesobj[0]
			
		return {'value': hasil}
	
	# Isi rayon dan kota, berdasarkan customer
	def onchange_customer(self,cr,uid,ids,customer,context=None):
		hasil ={}
		if customer:
			customerClass = self.pool.get("mmr.customer")
			customerobj = customerClass.browse(cr,uid,customer)
			hasil['rayon'] = customerobj.rayon
			hasil['kota'] = customerobj.kota
		return {'value': hasil}
		
	_columns = {
		'sales': fields.many2one("mmr.sales", "Sales", required=True),
		'customer' : fields.many2one("mmr.customer", "Customer", required=True),
		'rayon' : fields.many2one("mmr.rayon","Rayon"),
		'kota' : fields.many2one("mmr.kota","Kota"),
		'tanggal' : fields.date("Tanggal Kunjungan", required=True),
		'laporan' : fields.text("Laporan"),
	}	
	
	def create(self,cr,uid,vals,context=None):
		id = super(mmr_laporansales,self).create(cr,uid,vals,context)
		if not self.browse(cr,uid,id).sales:
			raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Hanya sales yang dapat membuat laporan!"))
		
		return id
	
	def write(self,cr,uid,ids,vals,context=None):
		grupClass = self.pool.get("res.groups")
		grupobj = grupClass.search(cr,uid,[('name','=','Admin')])
		userClass = self.pool.get("res.users")
		grupditemukan = False
		for semuagrup in userClass.browse(cr,uid,uid).groups_id:
			if semuagrup.id == grupobj[0]:
				grupditemukan = True
		if uid != self.browse(cr,uid,ids).sales.userid.id and not grupditemukan:
			raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Hanya sales pembuat yang dapat mengedit laporan / pihak admin!"))
			
		return super(mmr_laporansales,self).write(cr, uid, ids, vals, context=context)
	
mmr_laporansales()

# Laporan penjualan untuk membantu marketing
# User dapat memfilter faktur berdasarkan beberapa macam variabel, sekaligus dapat melihat total faktur perbulan
# Dapat melihat rata - rata faktur
class mmr_laporanmarketing(osv.osv):
	_name = "mmr.laporanmarketing"
	_description = "Modul Laporan Marketing untuk PT. MMR."
	
	# Isi penjualan PO berdasarkan filter yang diinginkan
	# Dapatkan seluruh PO berdasarkan filter yang ada, lalu di intersect
	@api.one
	@api.onchange("load")
	def _isi_penjualanpo(self):
		self.load = False
		self.penjualanpo = False
		self.penjualanfaktur = False
		self.penjualanretur = False
		listcustomer = []
		listcustomerfaktur = []
		listcustomerretur = []
		if self.customer:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([('customer','=',self.customer.id)]):
				listcustomer.append(semuapenjualanpo.id)
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([('customer','=',self.customer.id)]):
				listcustomerfaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				if semuapenjualanretur.idpopenjualan.customer == self.customer:
					listcustomerretur.append(semuapenjualanretur.id)		
		else:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([]):
				listcustomer.append(semuapenjualanpo.id)
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([]):
				listcustomerfaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				listcustomerretur.append(semuapenjualanretur.id)		
		listrayon = []
		listrayonfaktur = []
		listrayonretur = []
		if self.rayon:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([('rayon','=',self.rayon.id)]):
				listrayon.append(semuapenjualanpo.id)
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([('rayon','=',self.rayon.id)]):
				listrayonfaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				if semuapenjualanretur.idpopenjualan.rayon == self.rayon:
					listrayonretur.append(semuapenjualanretur.id)	
		else:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([]):
				listrayon.append(semuapenjualanpo.id)	
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([]):
				listrayonfaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				listrayonretur.append(semuapenjualanretur.id)		
		listkota = []
		listkotafaktur = []
		listkotaretur = []
		if self.kota:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([('kota','=',self.kota.id)]):
				listkota.append(semuapenjualanpo.id)
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([('kota','=',self.kota.id)]):
				listkotafaktur.append(semuapenjualanfaktur.id)
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				if semuapenjualanretur.idpopenjualan.kota == self.kota:
					listkotaretur.append(semuapenjualanretur.id)	
		else:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([]):
				listkota.append(semuapenjualanpo.id)
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([]):
				listkotafaktur.append(semuapenjualanfaktur.id)
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				listkotaretur.append(semuapenjualanretur.id)		
		liststarttanggal = []
		liststarttanggalfaktur = []
		liststarttanggalretur = []
		if self.starttanggal:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([('tanggal','>=',self.starttanggal)]):
				liststarttanggal.append(semuapenjualanpo.id)
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([('tanggalterbit','>=',self.starttanggal)]):
				liststarttanggalfaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([('tanggalterbit','>=',self.starttanggal)]):
				liststarttanggalretur.append(semuapenjualanretur.id)	
		else:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([]):
				liststarttanggal.append(semuapenjualanpo.id)
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([]):
				liststarttanggalfaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				liststarttanggalretur.append(semuapenjualanretur.id)
		listendtanggal = []
		listendtanggalfaktur = []
		listendtanggalretur = []
		if self.endtanggal:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([('tanggal','<=',self.endtanggal)]):
				listendtanggal.append(semuapenjualanpo.id)
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([('tanggalterbit','<=',self.endtanggal)]):
				listendtanggalfaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([('tanggalterbit','<=',self.endtanggal)]):
				listendtanggalretur.append(semuapenjualanretur.id)	
		else:
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([]):
				listendtanggal.append(semuapenjualanpo.id)			
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([]):
				listendtanggalfaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				listendtanggalretur.append(semuapenjualanretur.id)	
		listteknisifaktur = []
		listteknisiretur = []
		if self.teknisi == True:
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([('teknisi','=',True)]):
				listteknisifaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([('teknisi','=',True)]):
				listteknisiretur.append(semuapenjualanretur.id)
		else:
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([]):
				listteknisifaktur.append(semuapenjualanfaktur.id)	
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				listteknisiretur.append(semuapenjualanretur.id)	
								
		listintersect = set.intersection(set(listcustomer),set(listrayon),set(listkota),set(liststarttanggal),set(listendtanggal))
		listintersectfaktur = set.intersection(set(listcustomerfaktur),set(listrayonfaktur),set(listkotafaktur),set(liststarttanggalfaktur),set(listendtanggalfaktur),set(listteknisifaktur))
		listintersectretur = set.intersection(set(listcustomerretur),set(listrayonretur),set(listkotaretur),set(liststarttanggalretur),set(listendtanggalretur),set(listteknisiretur))
		
		for semuaid in listintersect:
			self.penjualanpo += self.env['mmr.penjualanpo'].browse(semuaid)
			
		for semuaid in listintersectfaktur:
			self.penjualanfaktur += self.env['mmr.penjualanfaktur'].browse(semuaid)	
		
		for semuaid in listintersectretur:
			self.penjualanretur += self.env['mmr.penjualanretur'].browse(semuaid)
	
	# Total perbulan faktur yang terpilih ( Berdasarkan filter)			
	@api.one
	@api.onchange("berdasarkan")
	def _isi_grafik(self):
		self.load = False
		if self.starttanggal and self.endtanggal:	
			starttanggal =  datetime.datetime.strptime(self.starttanggal,'%Y-%m-%d')
			
			endtanggal = datetime.datetime.strptime(self.endtanggal,'%Y-%m-%d')
			jumlahbulan =  	abs((starttanggal.year - endtanggal.year)*12 + starttanggal.month - endtanggal.month) + 1
			
			listpencapaian = {}
			idxbulan = starttanggal.month
			for idx in range(0,jumlahbulan):
				listpencapaian[idxbulan%12] = 0
				idxbulan+=1
			
			
			listberdasarkan = {}
			if self.berdasarkan == 'customer':
				for semuapenjualanfaktur in self.penjualanfaktur:
					if semuapenjualanfaktur.customer.nama in listberdasarkan:
						if not self.teknisi or (self.teknisi and semuapenjualanfaktur.teknisi):
							listberdasarkan[semuapenjualanfaktur.customer.nama][(datetime.datetime.strptime(semuapenjualanfaktur.tanggalterbit,'%Y-%m-%d').month)%12] += semuapenjualanfaktur.hppembelian
					else:
						listberdasarkan[semuapenjualanfaktur.customer.nama] = listpencapaian.copy()
						if ((not self.teknisi) or (self.teknisi and semuapenjualanfaktur.teknisi)):
							listberdasarkan[semuapenjualanfaktur.customer.nama][(datetime.datetime.strptime(semuapenjualanfaktur.tanggalterbit,'%Y-%m-%d').month)%12] = semuapenjualanfaktur.hppembelian
				for semuapenjualanretur in self.penjualanretur:
					if semuapenjualanretur.idpopenjualan.customer.nama in listberdasarkan:
						listberdasarkan[semuapenjualanretur.idpopenjualan.customer.nama][(datetime.datetime.strptime(semuapenjualanretur.tanggalterbit,'%Y-%m-%d').month)%12] -= semuapenjualanretur.hppembelian
					else:
						listberdasarkan[semuapenjualanretur.idpopenjualan.customer.nama][(datetime.datetime.strptime(semuapenjualanretur.tanggalterbit,'%Y-%m-%d').month)%12] = -1*semuapenjualanretur.hppembelian			
			elif self.berdasarkan == 'rayon':
				for semuapenjualanfaktur in self.penjualanfaktur:
					if semuapenjualanfaktur.rayon.kode in listberdasarkan:
						if ((not self.teknisi) or (self.teknisi and semuapenjualanfaktur.teknisi)):
							listberdasarkan[semuapenjualanfaktur.rayon.kode][(datetime.datetime.strptime(semuapenjualanfaktur.tanggalterbit,'%Y-%m-%d').month)%12] += semuapenjualanfaktur.hppembelian
					else:
						listberdasarkan[semuapenjualanfaktur.rayon.kode] = listpencapaian.copy()
						if ((not self.teknisi) or (self.teknisi and semuapenjualanfaktur.teknisi)):
							listberdasarkan[semuapenjualanfaktur.rayon.kode][(datetime.datetime.strptime(semuapenjualanfaktur.tanggalterbit,'%Y-%m-%d').month)%12] = semuapenjualanfaktur.hppembelian
				for semuapenjualanretur in self.penjualanretur:
					if semuapenjualanretur.idpopenjualan.rayon.kode in listberdasarkan:
						listberdasarkan[semuapenjualanretur.idpopenjualan.rayon.kode][(datetime.datetime.strptime(semuapenjualanretur.tanggalterbit,'%Y-%m-%d').month)%12] -= semuapenjualanretur.hppembelian
					else:
						listberdasarkan[semuapenjualanretur.idpopenjualan.rayon.kode][(datetime.datetime.strptime(semuapenjualanretur.tanggalterbit,'%Y-%m-%d').month)%12] = -1*semuapenjualanretur.hppembelian			
			
			elif self.berdasarkan == 'kota':
				for semuapenjualanfaktur in self.penjualanfaktur:
					if semuapenjualanfaktur.kota.nama in listberdasarkan:
						if ((not self.teknisi) or (self.teknisi and semuapenjualanfaktur.teknisi)):
							listberdasarkan[semuapenjualanfaktur.kota.nama][(datetime.datetime.strptime(semuapenjualanfaktur.tanggalterbit,'%Y-%m-%d').month)%12] += semuapenjualanfaktur.hppembelian
					else:
						listberdasarkan[semuapenjualanfaktur.kota.nama] = listpencapaian.copy()
						if ((not self.teknisi) or (self.teknisi and semuapenjualanfaktur.teknisi)):
							listberdasarkan[semuapenjualanfaktur.kota.nama][(datetime.datetime.strptime(semuapenjualanfaktur.tanggalterbit,'%Y-%m-%d').month)%12] = semuapenjualanfaktur.hppembelian
				for semuapenjualanretur in self.penjualanretur:
					if semuapenjualanretur.idpopenjualan.kota.nama in listberdasarkan:
						listberdasarkan[semuapenjualanretur.idpopenjualan.kota.nama][(datetime.datetime.strptime(semuapenjualanretur.tanggalterbit,'%Y-%m-%d').month)%12] -= semuapenjualanretur.hppembelian
					else:
						listberdasarkan[semuapenjualanretur.idpopenjualan.kota.nama][(datetime.datetime.strptime(semuapenjualanretur.tanggalterbit,'%Y-%m-%d').month)%12] = -1*semuapenjualanretur.hppembelian			

			listbulan = {}
			listbulan['1'] = 0
			listbulan['2'] = 0
			listbulan['3'] = 0
			listbulan['4'] = 0
			listbulan['5'] = 0
			listbulan['6'] = 0
			listbulan['7'] = 0
			listbulan['8'] = 0
			listbulan['9'] = 0
			listbulan['10'] = 0		
			listbulan['11'] = 0
			listbulan['0'] = 0
			listbulan['jumlah'] = 0
			listbulan['rerata'] = 0	
				
			self.grafikpenjualan = False							
			for semuaberdasarkan in listberdasarkan:
				isigrafikpenjualan = {}
				isigrafikpenjualan['laporanmarketing'] = self.id
				isigrafikpenjualan['berdasarkan'] = semuaberdasarkan
				jumlah = 0
				for semuapencapaian in listberdasarkan[semuaberdasarkan]:
					isigrafikpenjualan[str(semuapencapaian)] = listberdasarkan[semuaberdasarkan][semuapencapaian]
					listbulan[str(semuapencapaian)] += listberdasarkan[semuaberdasarkan][semuapencapaian]
					listbulan["jumlah"] += listberdasarkan[semuaberdasarkan][semuapencapaian]
					jumlah += listberdasarkan[semuaberdasarkan][semuapencapaian]
				
				isigrafikpenjualan['jumlah'] = jumlah
				isigrafikpenjualan['rerata'] = round(jumlah / jumlahbulan,2)
				
				self.grafikpenjualan += self.env['mmr.grafikpenjualan'].new(isigrafikpenjualan)
			listbulan['laporanmarketing'] = self.id
			listbulan['berdasarkan'] = "~Total"
			listbulan['rerata'] = round(listbulan['jumlah'] / jumlahbulan,2)
			self.grafikpenjualan += self.env['mmr.grafikpenjualan'].new(listbulan)
				
		self.berdasarkantampilan = self.berdasarkan	
		self.berdasarkan = False	
		
	_columns = {
		'customer': fields.many2one("mmr.customer", "Customer"),
		'rayon': fields.many2one("mmr.rayon", "Rayon"),
		'kota': fields.many2one("mmr.kota", "Kota"),
		'starttanggal' : fields.date("Start"),
		'endtanggal' : fields.date("End"),
		'teknisi': fields.boolean("Teknisi(P)"),
		'penjualanpo': fields.one2many("mmr.penjualanpo", "laporanmarketing", "Penjualan PO"),
		'penjualanfaktur' : fields.one2many("mmr.penjualanfaktur", "laporanmarketing", "Penjualan Faktur"),
		'penjualanretur' : fields.one2many("mmr.penjualanretur", "laporanmarketing", "Penjualan Retur"),
		'grafikpenjualan' : fields.one2many("mmr.grafikpenjualan", "laporanmarketing", "Grafik Penjualan", compute="_isi_grafik"),
		'berdasarkan' : fields.selection([('rayon','Rayon'), ('customer','Customer'), ('kota','Kota')], "Berdasarkan"),
		'berdasarkantampilan' : fields.char("Berdasarkan", readonly=True),
		'trigger' : fields.char("Trigger", compute="_isi_penjualanpo"),
		'load' : fields.boolean("Filter!"),
	}	
	
mmr_laporanmarketing()	

class mmr_grafikpenjualan(osv.osv):
	_name = "mmr.grafikpenjualan"
	_description = "Modul Grafik Penjualan untuk PT. MMR."
	
	_columns = {
		'laporanmarketing' : fields.many2one("mmr.laporanmarketing"),	
		'berdasarkan': fields.char("Berdasarkan"),
		'1' : fields.float("Januari", digits=(12,2)),
		'2' : fields.float("Februari", digits=(12,2)),
		'3' : fields.float("Maret", digits=(12,2)),
		'4' : fields.float("April", digits=(12,2)),
		'5' : fields.float("Mei", digits=(12,2)),
		'6' : fields.float("Juni", digits=(12,2)),
		'7' : fields.float("Juli", digits=(12,2)),
		'8' : fields.float("Agustus", digits=(12,2)),
		'9' : fields.float("September", digits=(12,2)),
		'10' : fields.float("Oktober", digits=(12,2)),
		'11' : fields.float("November", digits=(12,2)),
		'0' : fields.float("Desember", digits=(12,2)),
		'jumlah' : fields.float("Jumlah", digits=(12,2)),
		'rerata' : fields.float("Rerata", digits=(12,2)),
	}	
	
mmr_grafikpenjualan()
