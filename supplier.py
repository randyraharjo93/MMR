from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools,api
import datetime
import itertools 

class mmr_supplier(osv.osv):
	_name = "mmr.supplier"
	_description = "Modul supplier untuk PT. MMR."
	_rec_name = "kode"
	
	# Hitung total hutang supplier
	def _hitung_hutang(self, cr, uid, ids, field_name, arg, context):
		res = {}
		popembelianClass = self.pool.get("mmr.pembelianpo")
		pembayaranpembelianClass = self.pool.get("mmr.pembayaranpembelian")
		
		# Hitung Total Hutang, Cari Seluruh PO dengan supplier ini
		# Ambil seluruh fakturnya, jumlahkan nettonya
		for supplier in self.browse(cr,uid,ids):
			total = 0
			for semuapo in popembelianClass.browse(cr,uid,popembelianClass.search(cr,uid,[('supplier','=',supplier.id)])):
				for semuafaktur in semuapo.pembelianfaktur:
					total+=semuafaktur.netto
			for semuapembayaran in pembayaranpembelianClass.browse(cr,uid,pembayaranpembelianClass.search(cr,uid,[('supplier','=',supplier.id)])):
				total-=semuapembayaran.bayar		
			res[supplier.id] = total
					
		return res
	
	_columns = {
		'kode': fields.char("Kode", required=True, size=3),
		'nama': fields.char("Nama", required=True, size=30),
		'alamat': fields.char("Alamat", size=60),
		'telp': fields.char("Telepon"),
		'hutang': fields.function(_hitung_hutang, type="float", method=True, string="Hutang", digits=(12,2)),
		'npwp': fields.char("NPWP"),
		'batashutang': fields.float("Batas Hutang", digits=(12,2)),
		'syaratpembayaran': fields.many2one("mmr.syaratpembayaran", "Syarat Pembayaran"),
		'listrekening': fields.one2many("mmr.nomorrekening", "supplier", "List Rekening"),
		'listcp': fields.one2many("mmr.cp", "supplier", "List CP"),
		'notes' : fields.text("Notes"),
	}	
	
	def create(self,cr,uid,vals,context=None):
		id = super(mmr_supplier,self).create(cr,uid,vals,context)
		
		validasisupplier(self,cr,uid,id)
		
		return id
	
	def write(self,cr,uid,ids,vals,context=None):
		super(mmr_supplier,self).write(cr, uid, ids, vals, context=context)
		
		validasisupplier(self,cr,uid,ids)
		
		return super(mmr_supplier,self).write(cr, uid, ids, vals, context=context)
	
mmr_supplier()

class mmr_nomorrekening(osv.osv):
	_name = "mmr.nomorrekening"
	_description = "Modul nomor rekening untuk PT. MMR."
	_rec_name = "nomor"
	
	# Tampilan Nomor rekening agar lengkap dengan bank dan atas nama
	def name_get(self,cr,uid,ids,context):
		res=[]
		for rekening in self.browse(cr,uid,ids,context):
			kalimatsatuan = "Bank: " + rekening.bank + " AN: " + rekening.atasnama + " No: " + rekening.nomor 
			
			res.append((rekening.id,kalimatsatuan))
		return res
	
	_columns = {
		'supplier': fields.many2one("mmr.supplier", "Supplier", ondelete="cascade"),
		'customer': fields.many2one("mmr.customer", "Customer", ondelete="cascade"),	
		'atasnama': fields.char("Atas Nama", required=True),
		'bank': fields.char("Bank", required=True),
		'nomor': fields.char("Nomor", required=True),
	}	
	
mmr_nomorrekening()

class mmr_cp(osv.osv):
	_name = "mmr.cp"
	_description = "Modul contact person untuk PT. MMR."
	_rec_name = "atasnama"
	
	# Tampilan CP Agar ada Atas Nama Telepon dan Alamat
	def name_get(self,cr,uid,ids,context):
		res=[]
		
		for cp in self.browse(cr,uid,ids,context):
			telp = cp.telp
			alamat = cp.alamat
			if cp.telp == False:
				telp = "-"
			if cp.alamat == False:
				alamat = "-"	
			kalimatsatuan = "AN: " + cp.atasnama + " Telepon: " + telp + " Alamat: " + alamat 
			
			res.append((cp.id,kalimatsatuan))
		return res
	
	_columns = {
		'supplier': fields.many2one("mmr.supplier", "Supplier", ondelete="cascade"),	
		'customer': fields.many2one("mmr.customer", "Customer", ondelete="cascade"),	
		'atasnama': fields.char("Atas Nama", required=True),
		'telp': fields.char("Telepon"),
		'alamat': fields.char("Alamat"),
	}	
	
mmr_cp()

class mmr_syaratpembayaran(osv.osv):
	_name = "mmr.syaratpembayaran"
	_description = "Modul syarat pembayaran untuk PT. MMR."
	_rec_name = "nama"
	
	_columns = {
		'nama': fields.char("Nama", required=True),
		'lama': fields.integer("Lama(Hari)", required=True),
	}	
	
	_sql_constraints = [
        ('name_uniq', 'unique(nama)', 'Syarat Bayar Sudah Ada!')
    ]
	
mmr_syaratpembayaran()

class mmr_daftarhargasupplier(osv.osv):
	_name = "mmr.daftarhargasupplier"
	_description = "Modul daftar harga supplier untuk PT. MMR."
	
	@api.one
	@api.depends("diskon","harga")
	def _hitung_netto(self):
		self.netto = round(self.harga - (self.harga * self.diskon / 100),2)
		
	
	_columns = {
		'namaproduk': fields.many2one("mmr.produk", "Nama Produk", readonly=True),
		'supplier': fields.many2one("mmr.supplier", "Supplier", required=True),
		'harga': fields.float("Harga", required=True, digits=(12,2)),
		'diskon': fields.float("Diskon(%)", digits=(12,2)),
		'netto': fields.float("Netto", compute="_hitung_netto", store=True, digits=(12,2)),
		'tanggalefektif': fields.date("Tanggal Efektif", required=True),
		'lebihdari' : fields.float("Beli Lebih dari", digits=(12,2)),
		'notes' : fields.text("Notes")
	}	
	
mmr_daftarhargasupplier()	


def validasisupplier(self,cr,uid,id,context=None):
	thisObj = self.browse(cr,uid,id)
	searchIds = self.search(cr,uid,['|',('nama','=',thisObj.nama),('kode','=',thisObj.kode)])
		
	if len(searchIds)>1:
		raise osv.except_osv(_('Tidak Dapat Membuat'),_("Supplier Sudah Terdaftar!"))
		
	return True	
