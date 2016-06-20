from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools, api, models
from dateutil.relativedelta import relativedelta
import datetime
import itertools 

class mmr_merk(osv.osv):
	_name = "mmr.merk"
	_description = "Modul merk untuk PT. MMR."
	_rec_name = "merk"
	
	_columns = {
		'merk': fields.char("Merk", required=True),
		'notes' : fields.text("Notes"),
	}	
	
	_sql_constraints = [
        ('name_uniq', 'unique(merk)', 'Nama merk sudah terpakai!')
    ]
	
mmr_merk()	

class mmr_satuan(osv.osv):
	
	# Satuan produk dapat memiliki nama / tipe yang sama tetapi berbeda jumlah isi. ( Hanya untuk informasi )
	# Agar mempermudah user memahami Isi dipisah ke field yang berbeda.
	# Pada menu pemilihan satuan, Isi ditampilkan agar user dapat langsung memilih jenis satuan dan isinya.
	
	_name = "mmr.satuan"
	_description = "Modul satuan untuk PT. MMR."
	
	def name_get(self,cr,uid,ids,context):
		res=[]
		
		for satuan in self.browse(cr,uid,ids,context):
			kalimatsatuan = str(satuan.satuan) + " (Isi: " + str(satuan.isi) + ")"
			res.append((satuan.id,kalimatsatuan))
			
		return res
	
	_columns = {
		'satuan': fields.char("Satuan", required=True),
		'isi': fields.float("Isi", required=True, digits=(12,2)),
		'notes' : fields.text("Notes"),
	}	
		
mmr_satuan()

class mmr_kategori(osv.osv):
	
	# Produk diberi kategori agar mudah mengidentifikasi barang sejenis.
	# Agar user dapat melihat produk dalam kategori yang sama, diberi one2many pada menu kategori.
	
	_name = "mmr.kategori"
	_description = "Modul kategori untuk PT. MMR."
	_rec_name = "kategori"
	
	_columns = {
		'kategori': fields.char("Kategori", required=True),
		'listproduk': fields.one2many("mmr.produk", "kategori", "List Produk"),
		'notes' : fields.text("Notes"),
	}	
	
	_sql_constraints = [
        ('name_uniq', 'unique(kategori)', 'Kategori sudah ada!')
    ]
	
mmr_kategori()

class mmr_produk(osv.osv):
	
	# Produk yang diperjual belikan. Hanya ada satu macam produk, tidak ada konsinyasi
	# Memiliki Jumlah Produk, Nilai Produk, Status ( Apabila barang ada yang akan kadaluarsa, hampir habis, barang khusus, dll)
	# Memiliki Harga Jual Terendah, berdasarkan daftar harga beli, Pengumuman agar ketika sales / admin sales akan menjual barang ini
	# terdapat pengumuman akan kenaikan harga!
	# Tiap Produk memiliki beberapa STOK, Stok ini berasal dari pembelian. Stok akan menjadi sumber masuk produk ini
	# Tiap STOK memiliki beberapa STOK KELUAR, stok keluar ini akan mengurangi jumlah stok produk.
	
	_name = "mmr.produk"
	_description = "Modul produk untuk PT. MMR."
	_rec_name = "namaproduk"		
	
	# Gunakan field.Function
	# Hanya untuk informasi, untuk penghitungan diluar ini selalu hitung ulang jumlah stoknya!
	# Boros Waktu! Tetapi pertimbangan bahwa 1 produk tidak akan terlalu banyak transaksi ( < 1000)
	def _hitung_jumlah(self, cr, uid, ids, field_name, arg, context):
		res = {}
		stokClass = self.pool.get("mmr.stok")
		
		for produk in self.browse(cr,uid,ids):
			jumlah = 0
			for allstok in produk.stok:
				jumlah += allstok.debit
				for allstokkeluar in allstok.stokkeluar:
					jumlah -= allstokkeluar.jumlah
			res[produk.id] = jumlah	
			
		return res
	
	# Baca seluruh stok, apabila memiliki stok dengan status warning, ubah status produk ke warning
	# Agar ketika dilihat dari List View Langsung terlihat ( Akan diwarna merah )
	def _periksa_warning(self, cr, uid, ids, field_name, arg, context):
		res={}
		
		for semuaproduk in self.browse(cr,uid,ids):
			warning = False
			for allstok in semuaproduk.sisastok:
				if allstok.warning == True:
					warning = True
			if semuaproduk.jumlah < semuaproduk.minimalstok:
				warning = True		
			res[semuaproduk.id] = warning	
			
		return res	
	
	# Pakai field.function. Hanya untuk informasi!
	# Kalikan jumlah barang dengan !HARGA BELI! 		
	def _hitung_nilai(self, cr, uid, ids, field_name, arg, context):
		res = {}
		stokClass = self.pool.get("mmr.stok")
		
		for produk in self.browse(cr,uid,ids):
			nilai = 0
			for allstok in produk.stok:
				nilai += round((allstok.debit * allstok.produk.harga) - (allstok.debit * allstok.produk.harga * allstok.produk.diskon / 100),2)
				for allstokkeluar in allstok.stokkeluar:
					nilai -= round((allstokkeluar.jumlah * allstok.produk.harga) - (allstokkeluar.jumlah * allstok.produk.harga * allstok.produk.diskon / 100),2)
			res[produk.id] = nilai	
				
		return res	
		
	# Hitung Harga Jual Terendah dari, Nilai daftar harga yang berlaku + 15% (Belum Pajak)
	# Gunakan harga beli dengan lebih dari == 0!
	# Gunakan depends agar ketika user mengedit Harga beli di form produk, HJT secara on-the-fly terupdate
	@api.one
	@api.depends("daftarhargasupplier","daftarhargasupplier.netto")
	def	_hitung_hjt(self):
		tanggalterbaru= False
		hargaterbaru = False
		# Cari seluruh daftar harga yang terbaru dan tanggal efektif tidak lebih dari hari ini
		for semuaharga in self.daftarhargasupplier:
			if tanggalterbaru == False:
				if datetime.datetime.strptime(semuaharga.tanggalefektif,"%Y-%m-%d") < datetime.datetime.today() and semuaharga.lebihdari == 0:
					tanggalterbaru = datetime.datetime.strptime(semuaharga.tanggalefektif,"%Y-%m-%d")
					hargaterbaru = semuaharga
			else:
				if datetime.datetime.strptime(semuaharga.tanggalefektif,"%Y-%m-%d") < datetime.datetime.today() and datetime.datetime.strptime(semuaharga.tanggalefektif,"%Y-%m-%d") > tanggalterbaru and semuaharga.lebihdari == 0:
					tanggalterbaru = datetime.datetime.strptime(semuaharga.tanggalefektif,"%Y-%m-%d")
					hargaterbaru = semuaharga
		
		if hargaterbaru != False:
			self.hargajualterendah = round((hargaterbaru.netto + hargaterbaru.netto*15/100),2)			
	
	# HJT juga bisa diisi manual!
	@api.one
	@api.depends("daftarhargasupplier")
	def	_set_hjt(self):
		return True

	# Sisa Stok digunakan untuk merangkum seluruh stok dengan expdate yang sama, agar membantu user, terutama gudang
	# mengetahui sisa stok yang ada berdasarkan expdate nya.
	# Gunakan field.function karena hanya untuk informasi
	def _hitung_sisastok(self, cr, uid, ids, field_name, arg, context):
		sisastokClass = self.pool.get("mmr.sisastok")
		for semuaproduk in self.browse(cr,uid,ids):
			# Hapus record sebelum karena field.function dipanggil berulang
			sisastokClass.unlink(cr,uid,sisastokClass.search(cr,uid,[("namaproduk","=",semuaproduk.id)]))
			listexp = {}
			# Ambil semua stok, kelompokan yang kadaluarsa, gudang dan level kekhususan-nya sama.	
			for semuastok in semuaproduk.stok:
				if str(semuastok.kadaluarsa) +"|"+ str(semuastok.gudang.id) +"|"+ str(semuastok.stokkhusus) not in listexp:
					listexp[str(semuastok.kadaluarsa) +"|"+ str(semuastok.gudang.id)+"|"+ str(semuastok.stokkhusus)] = semuastok.debit - semuastok.kredit
				else:
					listexp[str(semuastok.kadaluarsa) +"|"+ str(semuastok.gudang.id) +"|"+ str(semuastok.stokkhusus)] +=  semuastok.debit
					listexp[str(semuastok.kadaluarsa) +"|"+ str(semuastok.gudang.id) +"|"+ str(semuastok.stokkhusus)] -=  semuastok.kredit
			# Berdasarkan kelompok yang ada, buat record kelas sisastok
			for semuaexp in listexp:
				tanggal,gudang,khusus = semuaexp.split("|")
				khususbool = False
				warning = False
				if tanggal == "False":
					tanggal = False
				else:
					plusbulan = datetime.datetime.today()+relativedelta(months=semuaproduk.bataskadaluarsa)
					if plusbulan >= datetime.datetime.strptime(tanggal,'%Y-%m-%d'):
						warning = True
				if khusus == "True":
					warning = True		
					khususbool = True
				# Unlink akan menyebabkan Method ini dipanggil dua kali oleh sebab itu, digunakan if ini agar hanya masuk 1x		
				if not sisastokClass.search(cr,uid,[("gudang","=",int(gudang)),("namaproduk","=",semuaproduk.id), ("kadaluarsa","=",tanggal),
													("saldo","=",listexp[semuaexp]),("warning","=",warning),('stokkhusus','=',khususbool)]):
					if listexp[semuaexp] > 0:	
						sisastokClass.create(cr,uid,{'gudang': int(gudang), 'namaproduk': semuaproduk.id, 'kadaluarsa': tanggal,
															'saldo': listexp[semuaexp], 'warning': warning, 'stokkhusus':khususbool})
	
	# Pengumuman otomatis dihapys setelah 2 bulan semenjak pembuatan
	# Gunakan CRON, Print sesuatu untuk memastikan jalannya CRON		
	def _hapus_pengumuman(self, cr, uid, context=None):
		hasilsearch = self.browse(cr,uid,self.search(cr,uid,[('pengumuman','!=',False)]))
		
		for seluruhhasilsearch in hasilsearch:
			if datetime.datetime.today() - datetime.timedelta(days=60) > datetime.datetime.strptime(seluruhhasilsearch.waktupengumuman,'%Y-%m-%d'):
				vals = {}
				vals['pengumuman'] = False
				vals['waktupengumuman'] = False
				self.write(cr,uid,seluruhhasilsearch.id,vals)
		
		hasilsearch = self.pool.get('mmr.laporanstok').search(cr,uid,[])	
		for seluruhhasilsearch in hasilsearch:
			self.pool.get('mmr.laporanstok').unlink(cr,uid,seluruhhasilsearch)	
		print 'CRON Hapus Pengumuman called'		
		
	# Guna trigger, Karena apabila method one2many diberi function, yang didalamnya memanggil create, akan menghasilkan error looping
	# Kemungkinan : Function dibaca saat membuka form produk, Karena efek create, metode function dipanggil lagi ( System meyadari adanya
	# perubahan data dan harus memanggil function sekali lagi ), Terjadi berulang hingga error looping
	_columns = {
		'merk': fields.many2one("mmr.merk","Merk",required=True),
		'namaproduk': fields.char("Nama",required=True, size = 35),
		'satuan': fields.many2one("mmr.satuan", "Satuan", required=True),
		'kategori': fields.many2one("mmr.kategori", "Kategori"),
		'bataskadaluarsa': fields.integer("Batas Kadaluarsa(Bulan)"),
		"hargajualterendah": fields.float("Harga Jual Terendah", compute="_hitung_hjt", inverse="_set_hjt", digits=(12,2), store=True, help="Didapat dari daftar harga terbaru +15%, kecuali diisi oleh otoritas."),
		"jumlah": fields.function(_hitung_jumlah, type="float",method=True, string="Jumlah", digits=(12,2)),
		"nilai" : fields.function(_hitung_nilai, type="float", digits=(12,2),method=True, string="Nilai", help="Didapat dari bruto pembelian produk ini."),
		'notes' : fields.text("Notes"),
		'stok': fields.one2many("mmr.stok", "namaproduk", "Kartu Stok", readonly=True),
		'sisastok': fields.one2many("mmr.sisastok", "namaproduk", "Sisa Stok"),
		'minimalstok' : fields.float("Minimal Persediaan", digits=(12,2)),
		'trigger': fields.function(_hitung_sisastok, type="char", string = "Trigger"),
		'daftarhargasupplier': fields.one2many("mmr.daftarhargasupplier",'namaproduk',"Daftar Harga Supplier"),
		'daftarhargacustomer': fields.one2many("mmr.daftarhargacustomer",'namaproduk',"Daftar Harga Customer"),
		'warning': fields.function(_periksa_warning,type="boolean", string="Warning", help="Apabila tercentang, ada barang hampir kadaluarsa atau stok hampir habis"),
		'gambar': fields.binary("Gambar", help="Masukkan Gambar di Sini"),
		'pengumuman' : fields.char("Pengumuman"),
		'waktupengumuman' : fields.date("Waktu Pengumuman"),
	}	

	def create(self,cr,uid,vals,context=None):
		if 'pengumuman' in vals and vals['pengumuman'] != False:
			vals['waktupengumuman'] = datetime.date.today()
		id = super(mmr_produk,self).create(cr,uid,vals,context)
		
		# Jangan sampai ada produk dengan merk dan nama yang sama
		thisObj = self.browse(cr,uid,id)
		searchIds = self.search(cr,uid,[('namaproduk','=',thisObj.namaproduk),('merk','=',thisObj.merk.id)])
		
		# Apabila ada barang lain ( Ada barang sama lebih dari 1 )
		if len(searchIds)>1:
			raise osv.except_osv(_('Tidak Dapat Membuat'),_("Barang Sudah Terdaftar!"))
		
		return id
	
	def write(self,cr,uid,id,vals,context=None):
		if 'pengumuman' in vals and vals['pengumuman'] != False:
			vals['waktupengumuman'] = datetime.date.today()
		res = super(mmr_produk,self).write(cr,uid,id,vals,context)
		
		# Jangan sampai ada produk dengan merk dan nama yang sama
		thisObj = self.browse(cr,uid,id)
		searchIds = self.search(cr,uid,[('namaproduk','=',thisObj.namaproduk),('merk','=',thisObj.merk.id)])
		
		# Apabila ada barang lain ( Ada barang sama lebih dari 1 )
		if len(searchIds)>1:
			raise osv.except_osv(_('Tidak Dapat Membuat'),_("Barang Sudah Terdaftar!"))

		return res
	
mmr_produk()


class mmr_inventaris(osv.osv):
	_name = "mmr.inventaris"
	_description = "Modul inventaris untuk PT. MMR."
	_rec_name = "nama"
	
	# Nilai akhir == nilai awal - Seluruh penyusutan
	def _isi_nilaiakhir(self, cr, uid, ids, field_name, field_value, args=None, context=None):
		res = {}
		
		for inventaris in self.browse(cr,uid,ids):
			jumlah = inventaris.nilai
			for penyusutan in inventaris.penyusutan:
				jumlah -= penyusutan.jumlah
			res[inventaris.id] = jumlah
			
		return res
			
	_columns = {
		'nama': fields.char("Nama", required=True),
		'susutper' : fields.selection([('bulan','Bulan'), ('tahun','Tahun')], "Penyusutan tiap", required=True),
		'nilaisusut': fields.float("Nilai Penyusutan(%)", required=True, digits=(12,2)),
		"akunterkena" : fields.one2many("mmr.akundetil","sumberinventaris","Jurnal"),
		"nilai" : fields.float("Nilai", required=True, digits=(12,2)),
		'nilaiakhir' : fields.function(_isi_nilaiakhir, string="Nilai Akhir", method=True, type="float", digits=(12,2), help="Nilai Inventaris Setelah Dipotong Penyusutan pada Jurnal Penyesuaian"),
		'nomorakunpenyusutan' :fields.many2one("mmr.akun","Nomor Akun Penyusutan", required=True),
		'penyusutan' : fields.one2many("mmr.penyusutan","idinventaris","Penyusutan"),
		"tanggal": fields.date("Tanggal", required=True),
		'notes' : fields.text("Notes"),
	}	
	
	_sql_constraints = [
        ('name_uniq', 'unique(nama)', 'Inventaris sudah ada!')
    ]
	
mmr_inventaris()

class mmr_penyusutan(osv.osv):
	_name = "mmr.penyusutan"
	_description = "Modul penyusutan untuk PT. MMR."
	
	_columns = {
		'idinventaris': fields.many2one("mmr.inventaris","IDINVENTRARIS", required=True),
		"tanggal": fields.date("Tanggal", required=True),
		'jumlah' : fields.float("Nilai Susut", required=True, digits=(12,2)),
		'notes' : fields.text("Notes"),
	}	
	
mmr_penyusutan()


