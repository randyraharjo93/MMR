from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools,api
from dateutil.relativedelta import relativedelta
from operator import attrgetter
import datetime
import itertools 
import calendar
import time

# SMART / ASSSISTANCE Digunakan untuk membantu user mengingat pekerjaanya.
# Daftar hal yang diingatkan tertulis dibawah ( tiap potongan program )
class mmr_smart(osv.osv):
	_name = "mmr.smart"
	_description = "Modul SMART untuk PT. MMR."
	_rec_name = "status"
	
	@api.one
	@api.onchange("status","milik")
	def _isi_pekerjaan(self):
		#PEKERJAAN GUDANG
		self.pekerjaan = False
		self.status = False
		if self.milik == "gudang":
			#1. MENGINGATKAN BARANG AKAN HABIS
			#2. MENGINGATKAN BARANG AKAN KADALUARSA
			for semuaproduk in self.env['mmr.produk'].search([]):
				jumlah = 0
				for semuastok in semuaproduk.stok:
					jumlahstok = semuastok.debit
					jumlah += semuastok.debit
					for semuastokkeluar in semuastok.stokkeluar:
						jumlah -= semuastokkeluar.jumlah
						jumlahstok -= semuastokkeluar.jumlah
					plusbulan = datetime.datetime.today()+relativedelta(months=semuaproduk.bataskadaluarsa)
					if jumlahstok > 0 and semuastok.kadaluarsa != False and plusbulan >= datetime.datetime.strptime(semuastok.kadaluarsa,'%Y-%m-%d'):
						kalimatsumber = "Produk: " + str(semuaproduk.merk.merk) + " " + str(semuaproduk.namaproduk) + "(" + str(semuaproduk.satuan.satuan) + " isi: " + str(semuaproduk.satuan.isi) + ")"
						kalimatdeskripsi = "Mendekati Batas Kadaluarsa" + " (Kadaluarsa: " + str(semuastok.kadaluarsa) + ")"
						if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
							self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Gudang", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
					
					#3. MENGIGATKAN BARANG PINJAMAN
					if jumlahstok > 0 and semuastok.stokkhusus:
						kalimatsumber = "Produk: " + str(semuaproduk.merk.merk) + " " + str(semuaproduk.namaproduk) + "(" + str(semuaproduk.satuan.satuan) + " isi: " + str(semuaproduk.satuan.isi) + ")"
						kalimatdeskripsi = "Masih memiliki barang pinjaman"
						if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
							self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Gudang", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})

								
				if jumlah < semuaproduk.minimalstok: 
					kalimatsumber = "Produk: " + str(semuaproduk.merk.merk) + " " + str(semuaproduk.namaproduk) + "(" + str(semuaproduk.satuan.satuan) + " isi: " + str(semuaproduk.satuan.isi) + ")" 
					kalimatdeskripsi = "Dibawah Minimal Persediaan" + " (Sedia: " + str(jumlah) + ", Minimal Persediaan: " +  str(semuaproduk.minimalstok) +")"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Gudang", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
			#4. MENGINGATKAN PO YANG MELEBIHI TANGGAL KEDATANGAN
			for semuapopembelian in self.env['mmr.pembelianpo'].search([]):
				jumlah = 0
				jumlahditerima = 0
				for semuapopembeliandetil in semuapopembelian.pembelianpodetil:
					jumlah += semuapopembeliandetil.jumlah
					jumlahditerima += semuapopembeliandetil.jumlahditerima
					
				if jumlah > jumlahditerima and semuapopembelian.tanggaldijanjikan!= False and datetime.datetime.strptime(semuapopembelian.tanggaldijanjikan,'%Y-%m-%d')- relativedelta(days=1) <= datetime.datetime.today() and semuapopembelian.dibatalkan == False:
					kalimatsumber = "PO: " + str(semuapopembelian.nomorpo)
					kalimatdeskripsi = "Mendekati / Terlambat Diterima" +  " (Tanggal Perkiraan: " + str(semuapopembelian.tanggaldijanjikan) +")"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Gudang", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})

		#PEKERJAAN AKUNTING			
		if self.milik == "akunting":
			listsj = self.env['mmr.pembeliansj'].search([])
			#1. MENGINGATKAN JURNAL YANG TIDAK BALANCE
			#1.1. Faktur Pembelian
			for semuafakturpembelian in self.env['mmr.pembelianfaktur'].search([]):		
				total = 0
				for semuaakundetil in semuafakturpembelian.akunterkena:
					total+=semuaakundetil.debit
					total-=semuaakundetil.kredit
						
				if round(total,2)!=0:
					kalimatsumber = "Faktur Pembelian: " + str(semuafakturpembelian.nomorfaktur)
					kalimatdeskripsi = "Jurnal Tidak Balance"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})	
				
				#  Sambil filter SJ yang sudah difakturkan
				if semuafakturpembelian.pembeliansj1 in listsj:
					listsj-=semuafakturpembelian.pembeliansj1	
				if semuafakturpembelian.pembeliansj2 in listsj:
					listsj-=semuafakturpembelian.pembeliansj2 	
				if semuafakturpembelian.pembeliansj3 in listsj:
					listsj-=semuafakturpembelian.pembeliansj3 	
				if semuafakturpembelian.pembeliansj4 in listsj:
					listsj-=semuafakturpembelian.pembeliansj4 	
				if semuafakturpembelian.pembeliansj5 in listsj:
					listsj-=semuafakturpembelian.pembeliansj5 	
				
				#3. Mengingatkan Faktur Belum Disetujui
				if not semuafakturpembelian.disetujui:
					kalimatsumber = "Faktur: " + str(semuafakturpembelian.nomorfaktur) +", pada PO: " + str(semuafakturpembelian.idpo.nomorpo)
					kalimatdeskripsi = "Belum Disetujui"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
	
			
			#2. Mengingatkan SJ Belum difaktur
			for semualistsj in listsj:
				if not semualistsj.idpo.pokhusus:
					kalimatsumber = "PO: " + str(semualistsj.idpo.nomorpo) +", SJ: " + str(semualistsj.nomorsj)
					kalimatdeskripsi = "Belum Difaktur"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
			
			listsj = self.env['mmr.penjualansj'].search([])
			#1.2. Faktur Penjualan			
			for semuafakturpenjualan in self.env['mmr.penjualanfaktur'].search([]):		
				total = 0
				for semuaakundetil in semuafakturpenjualan.akunterkena:
					total+=semuaakundetil.debit
					total-=semuaakundetil.kredit
						
				if round(total,2)!=0:
					kalimatsumber = "Faktur Penjualan: " + str(semuafakturpenjualan.nomorfaktur)
					kalimatdeskripsi = "Jurnal Tidak Balance"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
			
				if semuafakturpenjualan.penjualansj in listsj:
					listsj-=semuafakturpenjualan.penjualansj
					
				#3. Mengingatkan Faktur Belum Disetujui	
				if not semuafakturpenjualan.disetujui:
					kalimatsumber = "Faktur: " + str(semuafakturpenjualan.nomorfaktur) +", pada PO: " + str(semuafakturpenjualan.idpenjualanpo.nomorpo)
					kalimatdeskripsi = "Belum Disetujui"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})

			#2. Mengingatkan SJ Belum difaktur			
			for semualistsj in listsj:
				if not semualistsj.idpenjualanpo.tanpafaktur:
					kalimatsumber = "PO: " + str(semualistsj.idpenjualanpo.nomorpo) +", SJ: " + str(semualistsj.nomorsj)
					kalimatdeskripsi = "Belum Difaktur"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
	
			#1.3. Pembayaran Pembelian			
			for semuapembayaranpembelian in self.env['mmr.pembayaranpembelian'].search([]):		
				total = 0
				for semuaakundetil in semuapembayaranpembelian.akunterkena:
					total+=semuaakundetil.debit
					total-=semuaakundetil.kredit
						
				if round(total,2)!=0:
					kalimatsumber = "Pembayaran ke Supplier: " + str(semuapembayaranpembelian.supplier.nama) + ", Tanggal: " + str(semuapembayaranpembelian.tanggalbayar)
					kalimatdeskripsi = "Jurnal Tidak Balance"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
			
			
			#1.4. Pembayaran Penjualan
			for semuapembayaranpenjualan in self.env['mmr.pembayaranpenjualan'].search([]):		
				total = 0
				for semuaakundetil in semuapembayaranpenjualan.akunterkena:
					total+=semuaakundetil.debit
					total-=semuaakundetil.kredit
						
				if round(total,2)!=0:
					kalimatsumber = "Pembayaran dari Customer: " + str(semuapembayaranpenjualan.customer.nama) + ", Tanggal: " + str(semuapembayaranpenjualan.tanggalbayar)
					kalimatdeskripsi = "Jurnal Tidak Balance"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})

			#1.5. Biaya	
			for semuabiaya in self.env['mmr.biaya'].search([]):		
				total = 0
				for semuaakundetil in semuabiaya.akunterkena:
					total+=semuaakundetil.debit
					total-=semuaakundetil.kredit
						
				if round(total,2)!=0:
					kalimatsumber = "Biaya untuk: " + str(semuabiaya.detilkejadian) + ", Tanggal: " + str(semuabiaya.tanggal)
					kalimatdeskripsi = "Jurnal Tidak Balance"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
			
			#1.6. Kegiatan Akunting			
			for semuakegiatanakunting in self.env['mmr.kegiatanakunting'].search([]):		
				total = 0
				for semuaakundetil in semuakegiatanakunting.akunterkena:
					total+=semuaakundetil.debit
					total-=semuaakundetil.kredit
						
				if round(total,2)!=0:
					kalimatsumber = "Kejadian: " + str(semuakegiatanakunting.detilkejadian) + ", Tanggal: " + str(semuakegiatanakunting.tanggal)
					kalimatdeskripsi = "Jurnal Tidak Balance"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})

			#1.7. Jurnal Penyesuaian			
			for semuajurnalpenyesuaian in self.env['mmr.jurnalpenyesuaian'].search([]):	
				total = 0
				for semuaakundetil in semuajurnalpenyesuaian.akunterkena:
					total+=semuaakundetil.debit
					total-=semuaakundetil.kredit
				
				if round(total,2)!=0:
					kalimatsumber = "Penyesuaian Bulan: " + str(semuajurnalpenyesuaian.bulan) + ", Tahun: " + str(semuajurnalpenyesuaian.tahun)
					kalimatdeskripsi = "Jurnal Tidak Balance"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
					
			#1.8. Jurnal Penutup			
			for semuajurnalpenutup in self.env['mmr.jurnalpenutup'].search([]):		
				total = 0
				for semuaakundetil in semuajurnalpenutup.akunterkena:
					total+=semuaakundetil.debit
					total-=semuaakundetil.kredit
						
				if round(total,2)!=0:
					kalimatsumber = "Penutupan Bulan: " + str(semuajurnalpenutup.bulan) + ", Tahun: " + str(semuajurnalpenutup.tahun)
					kalimatdeskripsi = "Jurnal Tidak Balance"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
			
			#1.9. Inventaris			
			for semuainventaris in self.env['mmr.inventaris'].search([]):		
				total = 0
				for semuaakundetil in semuainventaris.akunterkena:
					total+=semuaakundetil.debit
					total-=semuaakundetil.kredit
						
				if round(total,2)!=0:
					kalimatsumber = "Inventaris: " + str(semuainventaris.nama)
					kalimatdeskripsi = "Jurnal Tidak Balance"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
			
		#4. Mengingatkan Retur Belum Dijurnal
			listretur = self.env['mmr.penjualanretur'].search(['|',('jurnalretur','=',False),('jurnalpembayaranretur','=',False)])
			for semuapenjualanretur in listretur:
				kalimatsumber = "Retur: " + str(semuapenjualanretur.nomorretur) + ", Tanggal : " + str(semuapenjualanretur.tanggalterbit)
				kalimatdeskripsi = "Belum Diselesaikan Jurnalnya"
				if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
					self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
		
		#5. Mengingatkan otoritas menjetujui retur
			listretur = self.env['mmr.penjualanretur'].search([('disetujui','=',False)])
			for semuapenjualanretur in listretur:
				kalimatsumber = "Retur: " + str(semuapenjualanretur.nomorretur) + ", Tanggal : " + str(semuapenjualanretur.tanggalterbit)
				kalimatdeskripsi = "Belum Disetujui Otoritas, segera laporkan"
				if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
					self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Akunting", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
		

		#PEKERJAAN ADMIN			
		if self.milik == "admin":				
			#1. PO AKAN MENDEKATI TANGGAL KIRIM
			#2. PO BELUM DISETUJUI
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([]):		
				jumlah = 0
				jumlahditerima = 0
				for semuapenjualanpodetil in semuapenjualanpo.penjualanpodetil:
					jumlah += semuapenjualanpodetil.jumlah
					jumlahditerima += semuapenjualanpodetil.jumlahdikirim
					
				if jumlah > jumlahditerima and semuapenjualanpo.tanggaldijanjikan!= False and datetime.datetime.strptime(semuapenjualanpo.tanggaldijanjikan,'%Y-%m-%d') - relativedelta(days=1) <= datetime.datetime.today() and semuapenjualanpo.dibatalkan == False:
					kalimatsumber = "PO: " + str(semuapenjualanpo.nomorpo)
					kalimatdeskripsi = "Segera Kirim" +  " (Tanggal Perkiraan: " + str(semuapenjualanpo.tanggaldijanjikan) +")"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Admin", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
				
				if semuapenjualanpo.disetujui == False and semuapenjualanpo.dibatalkan == False:
					kalimatsumber = "PO: " + str(semuapenjualanpo.nomorpo)
					kalimatdeskripsi = "Belum Valid (Kurang Persetujuan)"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Admin", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
		
		#PEKERJAAN SALES			
		if self.milik == "sales":				
			sales = self.env['mmr.sales'].search([('userid','=',self._uid)])	
			#1. PO AKAN MENDEKATI TANGGAL KIRIM
			#2. MENGINGATKAN PO YANG BELUM DISETUJUI	
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([('sales','=',sales.id)]):		
				jumlah = 0
				jumlahditerima = 0
				for semuapenjualanpodetil in semuapenjualanpo.penjualanpodetil:
					jumlah += semuapenjualanpodetil.jumlah
					jumlahditerima += semuapenjualanpodetil.jumlahdikirim
					
				if jumlah > jumlahditerima and semuapenjualanpo.tanggaldijanjikan!= False and datetime.datetime.strptime(semuapenjualanpo.tanggaldijanjikan,'%Y-%m-%d') - relativedelta(days=1) <= datetime.datetime.today() and semuapenjualanpo.dibatalkan == False:
					kalimatsumber = "PO: " + str(semuapenjualanpo.nomorpo)
					kalimatdeskripsi = "Segera Kirim" +  " (Tanggal Perkiraan: " + str(semuapenjualanpo.tanggaldijanjikan) +")"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Sales", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
				
				if semuapenjualanpo.disetujuisales.id	== False and semuapenjualanpo.dibatalkan == False:
					kalimatsumber = "PO: " + str(semuapenjualanpo.nomorpo)
					kalimatdeskripsi = "Belum Anda Setujui"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Sales", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})	
					
			#3. MENGINGATKAN BARANG YANG SUDAH LAMA TIDAK DIPESAN OLEH CUSTOMER (3 bln)
			listrayon = []
			for semuarayon in sales.listrayon:
				listrayon.append(semuarayon.id)	
			customer = self.env['mmr.customer'].search([('rayon','in',listrayon)])
			for semuacustomer in customer:
				listproduk = {}
				for semuapenjualanpo in self.env['mmr.penjualanpo'].search([('customer','=',semuacustomer.id),('dibatalkan','=',False)]):	
					for semuapenjualanpodetil in semuapenjualanpo.penjualanpodetil:
						if semuapenjualanpodetil.namaproduk in listproduk:
							if listproduk[semuapenjualanpodetil.namaproduk] < semuapenjualanpo.tanggal:
								listproduk[semuapenjualanpodetil.namaproduk] = semuapenjualanpo.tanggal
						else:
							listproduk[semuapenjualanpodetil.namaproduk] = semuapenjualanpo.tanggal
				for semualistproduk in listproduk:
					if datetime.datetime.strptime(listproduk[semualistproduk],'%Y-%m-%d') + relativedelta(months=3) < datetime.datetime.today():
						kalimatsumber = "Customer: " + str(semuacustomer.nama)
						kalimatdeskripsi = "3 Bulan Lebih Tidak Pesan: " + semualistproduk.namaproduk + " (Terakhir: " + str(listproduk[semualistproduk]) +")"
						if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
							self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Sales", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})	
							
		#PEKERJAAN KEPALA SALES			
		if self.milik == "kepalasales":
			#1. MENYETUJUI SELURUH PENJUALAN PO
			for semuapenjualanpo in self.env['mmr.penjualanpo'].search([]):		
				jumlah = 0
				jumlahditerima = 0
				for semuapenjualanpodetil in semuapenjualanpo.penjualanpodetil:
					jumlah += semuapenjualanpodetil.jumlah
					jumlahditerima += semuapenjualanpodetil.jumlahdikirim
					
				if semuapenjualanpo.disetujuisupervisor.id	== False and semuapenjualanpo.dibatalkan == False:
					kalimatsumber = "PO: " + str(semuapenjualanpo.nomorpo)
					kalimatdeskripsi = "Belum Anda Setujui"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Kepala Sales", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})	
		
		#PEKERJAAN KEUANGAN		
		if self.milik == "keuangan":	
			#1. JATUH TEMPO FAKTUR PEMBELIAN
			for semuapembelianfaktur in self.env['mmr.pembelianfaktur'].search([('lunas','=',False)]):		
					
				if semuapembelianfaktur.jatuhtempo != False and datetime.datetime.strptime(semuapembelianfaktur.jatuhtempo,'%Y-%m-%d') - relativedelta(days=1) <= datetime.datetime.today()  :
					kalimatsumber = "Faktur: " + str(semuapembelianfaktur.nomorfaktur)
					kalimatdeskripsi = "Mendekati / Terlambat Dibayar (Jatuh Tempo: " + str(semuapembelianfaktur.jatuhtempo) +")"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Keuangan", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})	
			#2. JATUH TEMPO FAKTUR PENJUALAN
			for semuapenjualanfaktur in self.env['mmr.penjualanfaktur'].search([('lunas','=',False)]):		
					
				if semuapenjualanfaktur.jatuhtempo != False and datetime.datetime.strptime(semuapenjualanfaktur.jatuhtempo,'%Y-%m-%d') - relativedelta(days=1) <= datetime.datetime.today()  :
					kalimatsumber = "Faktur: " + str(semuapenjualanfaktur.nomorfaktur)
					kalimatdeskripsi = "Mendekati / Terlambat Dibayar (Jatuh Tempo: " + str(semuapenjualanfaktur.jatuhtempo) +")"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Keuangan", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})	
			
			#3. MENYETUJUI PENCATATAN PEMBAYARAN PEMBELIAN
			for semuapembayaranpembelian in self.env['mmr.pembayaranpembelian'].search([('disetujui','=',False)]):
				kalimatsumber = "Pembayaran Pembelian Supplier: " + str(semuapembayaranpembelian.supplier.nama) + " Tanggal: " + str(semuapembayaranpembelian.tanggalbayar)
				kalimatdeskripsi = "Belum Disetujui"
				if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
					self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Keuangan", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})	

			#4. MENYETUJUI PENCATATAN PEMBAYARAN PENJUALAN
			for semuapembayaranpenjualan in self.env['mmr.pembayaranpenjualan'].search([('disetujui','=',False)]):
				kalimatsumber = "Pembayaran Penjualan Customer: " + str(semuapembayaranpenjualan.customer.nama) + " Tanggal: " + str(semuapembayaranpenjualan.tanggalbayar)
				kalimatdeskripsi = "Belum Disetujui"
				if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
					self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Keuangan", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})
		
			#4. PELUNASAN RETUR
			for semuapenjualanretur in self.env['mmr.penjualanretur'].search([]):
				if semuapenjualanretur.netto > semuapenjualanretur.dibayar:
					kalimatsumber = "Retur: " + str(semuapenjualanretur.nomorretur) + ", Tanggal: " + str(semuapenjualanretur.tanggalterbit)
					kalimatdeskripsi = "Belum Dibayar"
					if len(self.env['mmr.lupakanpekerjaan'].search([('write_uid','=',self._uid),('sumber','=',kalimatsumber),('deskripsi','=',kalimatdeskripsi)])) == 0:
						self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':"Keuangan", 'sumber':kalimatsumber, 'deskripsi':kalimatdeskripsi})

		#PEKERJAAN PRIBADI
		for pekerjaan in self.env['mmr.tambahpekerjaan'].search([('create_uid','=',self._uid)]):
			self.pekerjaan += self.pekerjaan.new({'pekerjaanmilik':self.env['res.users'].browse(self._uid).login, 'sumber':pekerjaan.sumber, 'deskripsi':pekerjaan.deskripsi})
			
		self.status = "TOTAL PEKERJAAN: " + str(len(self.pekerjaan)	)
			
	def _isi_omzet(self, cr, uid, context=None):
		salesClass = self.pool.get("mmr.sales")
		sales = salesClass.browse(cr,uid,salesClass.search(cr,uid,[('userid','=',uid)]))
		if sales:
			total = 0.0
			totaltarget = 0.0
			for semuarayon in sales.listrayon:
				for semuapopenjualan in semuarayon.listpopenjualan:
					for semuafakturpenjualan in semuapopenjualan.penjualanfaktur:
						if semuafakturpenjualan.tanggalterbit != False and datetime.datetime.strptime(semuafakturpenjualan.tanggalterbit,'%Y-%m-%d').strftime("%m") == datetime.datetime.today().strftime("%m"):
							total+=semuafakturpenjualan.netto	
			penjualanreturClass = self.pool.get("mmr.penjualanretur")
			hasilsearch = penjualanreturClass.search(cr,uid,[])
			
			for semuapenjualanretur in hasilsearch:
				penjualanrturobj = penjualanreturClass.browse(cr,uid,semuapenjualanretur)
				if datetime.datetime.strptime(penjualanrturobj.tanggalterbit,'%Y-%m-%d').strftime("%m") == datetime.datetime.today().strftime("%m") and penjualanrturobj.idpopenjualan.sales == sales:
					total-=penjualanrturobj.hppembelian					
			for semuarayon in sales.listrayon:
				totaltarget += semuarayon.target
			if totaltarget == 0:
				return 0
			else:
				return round(total / totaltarget * 100,2)
		return 0
       										
	_columns = {
		'status': fields.char("Status Pekerjaan", readonly=True),
		'targetomzet' : fields.float("Target Omzet", digits=(12,2)),
		'pekerjaan' : fields.one2many("mmr.pekerjaan","smart","Pekerjaan", readonly=True),
		'milik' : fields.selection([('gudang','Gudang'), ('akunting','Akunting'), ('admin','Admin')
										, ('sales','Sales'), ('kepalasales','Kepala Sales'), ('keuangan','Keuangan')
										], "Pekerjaan Milik", required=True),
		'trigger' : fields.char("Trigger", compute="_isi_pekerjaan")
	}
	
	_defaults = {
		'status': "Silahkan Tekan Tombol Reload Pekerjaan",		
		'targetomzet' : _isi_omzet,
				}	
	
mmr_smart()

class mmr_pekerjaan(osv.osv):
	_name = "mmr.pekerjaan"
	_description = "Modul Pekerjaan untuk PT. MMR."
	
	_columns = {
		'smart' : fields.many2one("mmr.smart","SMART"),
		'pekerjaanmilik' : fields.char("Pekerjaan Milik"),
		'sumber' : fields.char("Sumber"),
		'deskripsi' : fields.text("Deskripsi"),
	}	
	
mmr_pekerjaan()

# Apabila ada pekerjaan yang sudah tidak relevan , dapat diletakkan di sini agar tidak diingatkan terus
# Ex: Barang sampel yang memang tidak bisa diapa - apakan
class mmr_lupakanpekerjaan(osv.osv):
	_name = "mmr.lupakanpekerjaan"
	_description = "Modul Lupakan Pekerjaan untuk PT. MMR."
	
	_columns = {
		'sumber' : fields.char("Sumber", required=True),
		'deskripsi' : fields.text("Deskripsi", required=True),
	}	
	
mmr_lupakanpekerjaan()

# Apabila ada pekerjaan khusus / tambahan pribadi, dapat diletakkan di sini 
class mmr_tambahpekerjaan(osv.osv):
	_name = "mmr.tambahpekerjaan"
	_description = "Modul Tambah Pekerjaan untuk PT. MMR."
	
	_columns = {
		'sumber' : fields.char("Sumber", required=True),
		'deskripsi' : fields.text("Deskripsi", required=True),
	}	
	
mmr_lupakanpekerjaan()

# Program ingin menyimpan database secara berjalan ( 1 tahun, bulan berikutnya setelah lebih dari satu tahun dapat dihapus otomatis menggunakan
# form ini ), pada auto delete akan diberi preview dan pengaman sebelum data dihapus
class mmr_autodelete(osv.osv):
	_name = "mmr.autodelete"
	_description = "Modul auto delete untuk PT. MMR."
	
	_columns = {
		'bulan' : fields.selection([('01','Januari'), ('02','Februari'), ('03','Maret')
										, ('04','April'), ('05','Mei'), ('06','Juni'), ('07','Juli')
										, ('08','Agustus'), ('09','September'), ('10','Oktober'), ('11','November')
										, ('12','Desember')], "Bulan", required=True),
		'tahun' : fields.selection([('2015','2015'), ('2016','2016'), ('2017','2017')
										, ('2018','2018'), ('2019','2019'), ('2020','2020'), ('2021','2021')
										, ('2022','2022'), ('2023','2023'), ('2024','2024'), ('2025','2025')], "Tahun", required=True),
		'preview' : fields.boolean("Pengaman", help="Apabila Pengaman tercentang, artinya data hanya akan di-review tanpa didelete"),
		'datadihapus' : fields.text("Data akan dihapus", readonly=True),
		'deleted' : fields.boolean("Data Telah Terhapus?", readonly=True),
	}	
	
	_defaults={
			'preview':True
			}
	
	def autodelete(self,cr,uid,ids,context=None):
		objini = self.browse(cr,uid,ids)
		if not objini.deleted:
			text = "Menghapus seluruh jurnal bulan ini, diganti dengan rangkuman bulan ini: \n"
			#Rangkum Akunting Bulan tersebut
			akunClass = self.pool.get("mmr.akun")
			akunDetilClass = self.pool.get("mmr.akundetil")
			listakun = {}
			for semuaakun in akunClass.search(cr,uid,[]):
				akunobj = akunClass.browse(cr,uid,semuaakun)
				listakun[str(akunobj.id)] = 0
				for semuaakundetil in akunobj.akundetil:
					if int(datetime.datetime.strptime(semuaakundetil.tanggal,'%Y-%m-%d').month) == int(objini.bulan) and int(datetime.datetime.strptime(semuaakundetil.tanggal,'%Y-%m-%d').year) == int(objini.tahun):
						if akunobj.normaldi == "debit":
							listakun[str(akunobj.id)] += semuaakundetil.debit
							listakun[str(akunobj.id)] -= semuaakundetil.kredit
						elif akunobj.normaldi == "kredit":
							listakun[str(akunobj.id)] -= semuaakundetil.debit
							listakun[str(akunobj.id)] += semuaakundetil.kredit	
						if not objini.preview:	
							akunDetilClass.unlink(cr,uid,semuaakundetil.id)	
			if not objini.preview:				
				for semuaakun in listakun:
					tanggalperingkasan = "01" + objini.bulan + objini.tahun
					if akunClass.browse(cr,uid,int(semuaakun)).normaldi == "debit":
						akunDetilClass.create(cr,uid,{'idakun': int(semuaakun),'isidebit':listakun[semuaakun],'sumberjurnalringkasan' : objini.id})
					elif akunClass.browse(cr,uid,int(semuaakun)).normaldi == "kredit":
						akunDetilClass.create(cr,uid,{'idakun': int(semuaakun),'isikredit':listakun[semuaakun],'sumberjurnalringkasan' : objini.id})		
			for semuaakun in listakun:
				tanggalperingkasan = "01" + objini.bulan + objini.tahun
				if akunClass.browse(cr,uid,int(semuaakun)).normaldi == "debit":
					text += '	-' + str(akunClass.browse(cr,uid,int(semuaakun)).namaakun) + '-------debit: ' + str(listakun[semuaakun]) + "\n"	
				elif akunClass.browse(cr,uid,int(semuaakun)).normaldi == "kredit":
					text += '	-' + str(akunClass.browse(cr,uid,int(semuaakun)).namaakun) + '-------kredit: ' + str(listakun[semuaakun]) + "\n"		
			
			text += "\n \n"		
			text += "Biaya Dihapus: \n"		
			# Hapus Record yang hanya berhubungan lgsg dengan akunting (Biaya, Kegiatan Akunting, Penutup, Penyesuaian)
			biayaClass = self.pool.get("mmr.biaya")
			kegiatanakuntingClass = self.pool.get("mmr.kegiatanakunting")
			jurnalpenyesuaianClass = self.pool.get("mmr.jurnalpenyesuaian")
			jurnalpenutupClass = self.pool.get("mmr.jurnalpenutup")
			drange = calendar.monthrange(int(objini.tahun),int(objini.bulan))
			startdate = datetime.datetime(int(objini.tahun),int(objini.bulan),1)
			enddate = datetime.datetime(int(objini.tahun),int(objini.bulan),int(drange[1]),23,59,59)
			for seluruhbiaya in biayaClass.search(cr,uid,[('tanggal','>=',startdate),('tanggal','<=',enddate)]):
				text += "	-" + biayaClass.browse(cr,uid,seluruhbiaya).detilkejadian + " , Tanggal: " + biayaClass.browse(cr,uid,seluruhbiaya).tanggal + "\n"
				if not objini.preview:
					biayaClass.unlink(cr,uid,seluruhbiaya,context={'ijindelete' : True})
				
			text += "\n \n Kegiatan Akunting Dihapus: \n"		
			
			for seluruhkegiatanakunting in kegiatanakuntingClass.search(cr,uid,[('tanggal','>=',startdate),('tanggal','<=',enddate)]):
				text += "	-" + kegiatanakuntingClass.browse(cr,uid,seluruhkegiatanakunting).detilkejadian + " , Tanggal: " + kegiatanakuntingClass.browse(cr,uid,seluruhkegiatanakunting).tanggal + "\n"
				if not objini.preview:
					kegiatanakuntingClass.unlink(cr,uid,seluruhkegiatanakunting,context={'ijindelete' : True})	
				
			text += "\n \n"
			hasilsearch = jurnalpenyesuaianClass.search(cr,uid,[('bulan','=',objini.bulan),('tahun','=',objini.tahun)])
			for semuahasilsearch in hasilsearch:
				if not objini.preview:
					jurnalpenyesuaianClass.unlink(cr,uid,semuahasilsearch)
				text += "	-Jurnal Penyesuaian \n"
	
			text += "\n \n"
			hasilsearch = jurnalpenutupClass.search(cr,uid,[('bulan','=',objini.bulan),('tahun','=',objini.tahun)])
			for semuahasilsearch in hasilsearch:
				if not objini.preview:
					jurnalpenutupClass.unlink(cr,uid,semuahasilsearch)
				text += "	-Jurnal Penutup \n"
			# BACA PO pembelian , Apabila PO Beres(Sudah Disetujui, Sudah Dikirim) --> Baca Faktur --> Apabila Faktur Beres Pembayaran(Sudah disetujui) --> Baca Pembayaran(Sudah Disetujui)
			# --> Baca Stok, apabila stok keluar dari stok masuk barang pada PO juga beres (Disetujui, Stok sdh dikirim, Sdh pembayaran) 
			# --> Hapus PO, PO Detil, SJ, Stok, Faktur, Faktur detil, pembayaran, pembayaran detil, stok, PO Keluar, Stok Keluar.
			
			pembayaranpenjualandihapus = []	
			pembayaranpenjualandetildihapus = []		
			fakturpenjualandihapus = []	
			sjpenjualandihapus = []	
			sjpenjualandetildihapus = []
			stokkeluardihapus = []
			popenjualandihapus = []
			
			pembayaranpembeliandihapus = []	
			pembayaranpembeliandetildihapus = []	
			fakturpembeliandihapus = []
			stokdihapus = []
			pembeliansjdihapus = []
			popepembeliandihapus = []
			
			popembelianClass = self.pool.get("mmr.pembelianpo")
			sjpembelianClass = self.pool.get("mmr.pembeliansj")
			fakturpembelianClass = self.pool.get("mmr.pembelianfaktur")
			stokClass = self.pool.get("mmr.stok")
			pembayaranpembelianClass = self.pool.get("mmr.pembayaranpembelian")
			pembayaranpembeliandetilClass = self.pool.get("mmr.pembayaranpembeliandetil")
			
			popenjualanClass = self.pool.get("mmr.penjualanpo")
			sjpenjualanClass = self.pool.get("mmr.penjualansj")
			sjpenjualandetilClass = self.pool.get("mmr.penjualansjdetil")
			stokkeluarClass = self.pool.get("mmr.stokkeluar")
			fakturpenjualanClass = self.pool.get("mmr.penjualanfaktur")
			pembayaranpenjualanClass = self.pool.get("mmr.pembayaranpenjualan")
			pembayaranpenjualandetilClass = self.pool.get("mmr.pembayaranpenjualandetil")
			
			for semuapopembelian in popembelianClass.search(cr,uid,[('waktu','<=',enddate)]):
				valid = True
				semuapopembelianobj = popembelianClass.browse(cr,uid,semuapopembelian)
				if semuapopembelianobj.disetujui != False and semuapopembelianobj.status == "Barang Lengkap" and (semuapopembelianobj.statusfaktur == "Faktur lengkap" or semuapopembelianobj.statusfaktur == "Tanpa Faktur"):
					for semuafaktur in semuapopembelianobj.pembelianfaktur:
						if semuafaktur.disetujui != False and (semuafaktur.status == "Lunas" or semuafaktur.lunas) and datetime.datetime.strptime(semuafaktur.tanggalterbit,"%Y-%m-%d") <= enddate:
							for semuapembayaran in semuafaktur.listpembayaran:
								if semuapembayaran.idpembayaranpembelian.disetujui != False  and datetime.datetime.strptime(semuapembayaran.idpembayaranpembelian.tanggalbayar,"%Y-%m-%d") <= enddate:
									print 'a'
								else:
									valid = False	
						else:
							valid = False
					for semuasj in semuapopembelianobj.pembeliansj:
						if semuasj.disetujui != False and datetime.datetime.strptime(semuasj.tanggalterbit,"%Y-%m-%d") <= enddate:
							for semuasjdetil in semuasj.pembeliansjdetil:
								jumlah = semuasjdetil.debit
								listpopenjualan = []
								for semuastokkeluar in semuasjdetil.stokkeluar:
									if  datetime.datetime.strptime(semuastokkeluar.idpenjualanpo.tanggal,"%Y-%m-%d") <= enddate:
										if semuastokkeluar.idpenjualanpo not in listpopenjualan:
											listpopenjualan.append(semuastokkeluar.idpenjualanpo)	
									else:
										valid = False		
									jumlah -= semuastokkeluar.jumlah
								if jumlah != 0:
									valid = False
								for semuapopenjualan in listpopenjualan:
									if (semuapopenjualan.disetujuiadmin != False and semuapopenjualan.disetujuisupervisor != False and semuapopenjualan.status == "Barang Lengkap Dikirim" and (semuapopenjualan.statusfaktur == "Faktur lengkap" or semuapopenjualan.statusfaktur == "Tanpa Faktur")) or semuapopenjualan.dibatalkan != False:
										for semuasjpenjualan in semuapopenjualan.penjualansj:
											if semuasjpenjualan.disetujui != False and datetime.datetime.strptime(semuasjpenjualan.tanggalterbit,"%Y-%m-%d") <= enddate: 	
												print 'a'
											else:
												valid = False
										for semuafakturpenjualan in semuapopenjualan.penjualanfaktur:
											if datetime.datetime.strptime(semuafakturpenjualan.tanggalterbit,"%Y-%m-%d") <= enddate and (semuafakturpenjualan.status == "Lunas" or semuafakturpenjualan.lunas) and semuafakturpenjualan.disetujui != False:
												for semuapembayaranpenjualan in semuafakturpenjualan.listpembayaran:
													if semuapembayaranpenjualan.idpembayaranpenjualan.disetujui != False  and datetime.datetime.strptime(semuapembayaranpenjualan.idpembayaranpenjualan.tanggalbayar,"%Y-%m-%d") <= enddate:
														print 'a'
													else:
														valid = False	
											else:
												valid = False
									else:
										valid = False
						else:
							valid = False
				else:
					valid = False
				if valid:
					popepembeliandihapus.append(semuapopembelian)
					listpopenjualan = []	
					for semuapembeliansj in semuapopembelianobj.pembeliansj:
						for semuapembeliansjdetil in semuapembeliansj.pembeliansjdetil:	 				
							for semuastokkeluar in semuapembeliansjdetil.stokkeluar:
								if semuastokkeluar.idpenjualanpo not in listpopenjualan:
									listpopenjualan.append(semuastokkeluar.idpenjualanpo)	
					for semuapopenjualan in listpopenjualan:
						for semuafakturpenjualan in semuapopenjualan.penjualanfaktur:
							for semuapembayaranpenjualan in semuafakturpenjualan.listpembayaran:
								pembayaranpenjualandetildihapus.append(semuapembayaranpenjualan)
								if semuapembayaranpenjualan.idpembayaranpenjualan not in pembayaranpenjualandihapus:
									pembayaranpenjualandihapus.append(semuapembayaranpenjualan.idpembayaranpenjualan)
						fakturpenjualandihapus.append(semuafakturpenjualan)		
						for semuasjpenjualan in semuapopenjualan.penjualansj:
							for semuasjpenjualandetil in semuasjpenjualan.penjualansjdetil:
								sjpenjualandetildihapus.append(semuasjpenjualandetil)
							for semuastokkeluar in 	semuasjpenjualan.stokkeluar:
								stokkeluardihapus.append(semuastokkeluar)
							sjpenjualandihapus.append(semuasjpenjualan)	
						popenjualandihapus.append(semuapopenjualan)	
					for semuafakturpembelian in semuapopembelianobj.pembelianfaktur:
						for semuapembayaranpembelian in semuafakturpembelian.listpembayaran:
							pembayaranpembeliandetildihapus.append(semuapembayaranpembelian)
							if semuapembayaranpembelian.idpembayaranpembelian not in pembayaranpembeliandihapus:
								pembayaranpembeliandihapus.append(semuapembayaranpembelian.idpembayaranpembelian)	
						fakturpembeliandihapus.append(semuafakturpembelian)	
					for semuasjpembelian in semuapopembelianobj.pembeliansj:
						for semuasjpembeliandetil in semuasjpembelian.pembeliansjdetil:
							stokdihapus.append(semuasjpembeliandetil)
						pembeliansjdihapus.append(semuasjpembelian)	
			
				
			text += "PO Pembelian yang dihapus: \n \n"
			for semuapopembeliandihapus in 	popepembeliandihapus:	
				popembelianobj = popembelianClass.browse(cr,uid,semuapopembeliandihapus)
				text += "-" + str(popembelianobj.nomorpo) + "\n" + "	Surat Jalan Bersangkutan:" + "\n"
				for semuapembeliansj in popembelianobj.pembeliansj:
					text += "	-"  + str(semuapembeliansj.nomorsj) + "\n"
				text += "	Faktur Bersangkutan:" + "\n"	
				for semuapembelianfaktur in popembelianobj.pembelianfaktur:
					text += "	-" + str(semuapembelianfaktur.nomorfaktur) + "\n"
					text += "		Pembayaran Bersangkutan:" + "\n"	
					for semuapembayaranpembelian in semuapembelianfaktur.listpembayaran:
						text += "		-Tanggal: " + str(semuapembayaranpembelian.idpembayaranpembelian.tanggalbayar) + "\n"
				text += "\n"
			text += "PO Penjualan yang dihapus: \n \n"
			for semuapopenjualandihapus in popenjualandihapus:	
				text += "-" + str(semuapopenjualandihapus.nomorpo) + "\n" + "	Surat Jalan Bersangkutan:" + "\n"
				for semuapenjualansj in semuapopenjualandihapus.penjualansj:
					text += "	-"  + str(semuapenjualansj.nomorsj) + "\n"
				text += "	Faktur Bersangkutan:" + "\n"	
				for semuapenjualanfaktur in semuapopenjualandihapus.penjualanfaktur:
					text += "	-" + str(semuapenjualanfaktur.nomorfaktur) + "\n"
					text += "		Pembayaran Bersangkutan:" + "\n"	
					for semuapembayaranpenjualan in semuapenjualanfaktur.listpembayaran:
						text += "		-Tanggal: " + str(semuapembayaranpenjualan.idpembayaranpenjualan.tanggalbayar) + "\n"
				text += "\n"
			
			text += "Stok dihapus: \n \n"	
			for semuastokdihapus in stokdihapus:
				text += "	-Produk: "	+ semuastokdihapus.merk.merk + "," + semuastokdihapus.namaproduk.namaproduk + ", ("+ semuastokdihapus.satuan.satuan + " Isi: " + str(semuastokdihapus.satuan.isi) + ") , Masuk dari PO Pembelian: " + str(semuastokdihapus.idpembelianpo.nomorpo) + ", Jumlah : " +str(semuastokdihapus.debit)+ " Kadaluarsa: " + str(semuastokdihapus.kadaluarsa) + " LOT: " + str(semuastokdihapus.lot) 
				text += "\n 	Keluar: \n"
				for semuastokkeluar in 	semuastokdihapus.stokkeluar:
					text += "		-Dari PO Penjualan: "  + str(semuastokkeluar.idpenjualanpo.nomorpo) + ", Jumlah : " +str(semuastokkeluar.jumlah) 
				
			self.write(cr,uid,ids,{'datadihapus' : text})
			if not objini.preview:
				for semuapembayaranpenjualandetil in pembayaranpenjualandetildihapus:
					pembayaranpenjualandetilClass.unlink(cr,uid,semuapembayaranpenjualandetil.id,context={'ijindelete' : True})
				for semuapembayaranpenjualan in pembayaranpenjualandihapus:
					pembayaranpenjualanClass.unlink(cr,uid,semuapembayaranpenjualan.id,context={'ijindelete' : True})
				for semuafakturpenjualan in fakturpenjualandihapus:
					fakturpenjualanClass.unlink(cr,uid,semuafakturpenjualan.id,context={'ijindelete' : True})
				for semuasjpenjualandetil in sjpenjualandetildihapus:
					sjpenjualandetilClass.unlink(cr,uid,semuasjpenjualandetil.id,context={'ijindelete' : True})
				for semuastokkeluar in stokkeluardihapus:
					stokkeluarClass.unlink(cr,uid,semuastokkeluar.id,context={'ijindelete' : True})
				for semuasjpenjualan in sjpenjualandihapus:
					sjpenjualanClass.unlink(cr,uid,semuasjpenjualan.id,context={'ijindelete' : True})
				for semuapopenjualan in popenjualandihapus:
					popenjualanClass.unlink(cr,uid,semuapopenjualan.id,context={'ijindelete' : True})
				for semuapembayaranpembeliandetil in pembayaranpembeliandetildihapus:
					pembayaranpembeliandetilClass.unlink(cr,uid,semuapembayaranpembeliandetil.id,context={'ijindelete' : True})
				for semuapembayaranpembelian in pembayaranpembeliandihapus:
					pembayaranpembelianClass.unlink(cr,uid,semuapembayaranpembelian.id,context={'ijindelete' : True})
				for semuafakturpembelian in fakturpembeliandihapus:
					fakturpembelianClass.unlink(cr,uid,semuafakturpembelian.id,context={'ijindelete' : True})
				for semuastok in stokdihapus:
					stokClass.unlink(cr,uid,semuastok.id,context={'ijindelete' : True})
				for semuapembeliansj in pembeliansjdihapus:
					sjpembelianClass.unlink(cr,uid,semuapembeliansj.id,context={'ijindelete' : True})
				for semuapopembelian in popepembeliandihapus:
					popembelianClass.unlink(cr,uid,semuapopembelian,context={'ijindelete' : True})		
						
				self.write(cr,uid,ids,{'deleted':True})		
		else:
			raise osv.except_osv(_('Tidak Dapat Menghapus'),_("Data sudah dihapus!"))
					
		return True
	
mmr_autodelete()

# Cetak Faktur Beli / Faktur Jual / Stok / Kas Besar / Kas Kecil / Kas Lab / Kas Bank / Jurnal / Kartu Hutang  
class mmr_cetakbackup(osv.osv):
	_name = "mmr.cetakbackup"
	_description = "Modul Cetak Backup untuk PT. MMR."
	
	@api.one
	@api.depends("jenis","starttanggal","endtanggal")
	def _isi_fakturbelidetil(self):
		self.fakturbelidetil = False
		if self.starttanggal and self.endtanggal and self.jenis == "pembelian":
			for semuafakturbelidetil in self.env['mmr.stok'].search([('idpembelianfaktur.tanggalterbit','>=',self.starttanggal),('idpembelianfaktur.tanggalterbit','<=',self.endtanggal)]):
				self.fakturbelidetil += semuafakturbelidetil
		
	@api.one
	@api.depends("jenis","starttanggal","endtanggal")
	def _isi_fakturjualdetil(self):
		self.fakturjualdetil = False
		if self.starttanggal and self.endtanggal and self.jenis == "penjualan":
			for semuafakturjualdetil in self.env['mmr.cetakfaktur'].search([('idpenjualanfaktur.tanggalterbit','>=',self.starttanggal),('idpenjualanfaktur.tanggalterbit','<=',self.endtanggal)]):
				self.fakturjualdetil += semuafakturjualdetil
	
	@api.one
	@api.depends("jenis","starttanggal","endtanggal")
	def _isi_stok(self):
		self.stok = False
		if self.starttanggal and self.endtanggal and self.jenis == "stok":
			allproduk = self.env['mmr.produk'].search([])
			allprodukbymerk = {}
			for semuaproduk in allproduk:
				if semuaproduk.merk.merk not in allprodukbymerk:
					allprodukbymerk[semuaproduk.merk.merk] = [semuaproduk]
				else:
					allprodukbymerk[semuaproduk.merk.merk].append(semuaproduk)
			
			for semuamerk in allprodukbymerk:	
				print allprodukbymerk[semuamerk]		
				for semuaproduk in allprodukbymerk[semuamerk]:
					ijin = True
					for semuastok in self.stok:
						if semuastok.merk.id == semuaproduk.merk.id and semuastok.namaproduk.id == semuaproduk.id:
							ijin = False
					if ijin:		
						temp = self.env['mmr.laporanstok'].new({'idcetakbackup':self.id,
																	'merk':semuaproduk.merk.id,'namaproduk':semuaproduk.id,
																	'satuan':semuaproduk.satuan.id, 'cetak' : True})
						kartustok = {}
						for semuastok in semuaproduk.stok:
							kartustok['in'+str(semuastok.id)] = semuastok.idpembeliansj.tanggalterbit
							for semuastokkeluar in semuastok.stokkeluar:
								kartustok['ou'+str(semuastokkeluar.id)] = semuastokkeluar.idpenjualansj.tanggalterbit
						allstok = self.env['mmr.kartustok']
						kartustok = sorted(kartustok.iteritems(), key=lambda (k,v): (v,k))
						jumlah = 0
						nilai = 0
						for semuastok in kartustok:
							if semuastok[0][0:2] == "in":
								stokobj = self.env['mmr.stok'].browse(int(semuastok[0][2:]))
								jumlah += stokobj.debit
								nilai += round(stokobj.harga * stokobj.debit,2) - round(round(stokobj.harga * stokobj.debit,2) * stokobj.diskon / 100,2)
								if stokobj.idpembeliansj.tanggalterbit >= self.starttanggal and stokobj.idpembeliansj.tanggalterbit <= self.endtanggal:
									allstok += self.env['mmr.kartustok'].new({
																'laporanstok' : temp.id, 'sumber' : str(stokobj.idpembelianpo.nomorpo),
																'tanggal' : stokobj.idpembeliansj.tanggalterbit, 'gudang' : stokobj.gudang,
																'harga' : stokobj.harga, 'debit' : stokobj.debit, 'bruto': round(stokobj.harga * stokobj.debit,2),
																'diskon':stokobj.diskon, 'hppembelian': round(stokobj.harga * stokobj.debit,2) - round(round(stokobj.harga * stokobj.debit,2) * stokobj.diskon / 100,2),
																'kadaluarsa' : stokobj.kadaluarsa, 'lot': stokobj.lot, 'stokkhusus' : stokobj.idpembelianpo.pokhusus,'saldo':jumlah,
																'hargasetelahdiskon' : round((round(stokobj.harga * stokobj.debit,2) - round(round(stokobj.harga * stokobj.debit,2) * stokobj.diskon / 100,2)) / stokobj.debit,2),
																'nilai':nilai
																})
							else:
								stokkeluarobj = self.env['mmr.stokkeluar'].browse(int(semuastok[0][2:]))
								jumlah -= stokkeluarobj.jumlah
								stokobj = self.env['mmr.stok'].browse(stokkeluarobj.idstok.id)
								nilai -= round(stokobj.harga * stokkeluarobj.jumlah,2) - round(round(stokobj.harga * stokkeluarobj.jumlah,2) * stokobj.diskon / 100,2)
								if stokkeluarobj.idpenjualanpo.tanggal >= self.starttanggal and stokkeluarobj.idpenjualanpo.tanggal <= self.endtanggal:
									allstok += self.env['mmr.kartustok'].new({
																'laporanstok' : temp.id, 'sumber' : str(stokkeluarobj.idpenjualanpo.nomorpo),
																'tanggal' : stokkeluarobj.idpenjualanpo.tanggal, 'gudang' : stokkeluarobj.idstok.gudang,
																'harga' : stokkeluarobj.idstok.harga, 'kredit' : stokkeluarobj.jumlah, 'bruto': round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2),
																'diskon':stokkeluarobj.idstok.diskon, 'hppembelian': round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2) - round(round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2) * stokkeluarobj.idstok.diskon / 100,2),
																'kadaluarsa' : stokkeluarobj.idstok.kadaluarsa, 'lot': stokkeluarobj.idstok.lot, 'stokkhusus' : stokkeluarobj.idstok.idpembelianpo.pokhusus,'saldo':jumlah,
																'hargasetelahdiskon' : round((round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2) - round(round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2) * stokkeluarobj.idstok.diskon / 100,2)) / stokkeluarobj.jumlah,2),
																'nilai':nilai
															})		
						temp.write({'laporanstokdetil':self.env['mmr.kartustok']})	
						for semuaallstok in allstok:
							temp.laporanstokdetil += semuaallstok				
						self.stok += temp
						
	@api.one
	@api.depends("jenis","starttanggal","endtanggal")
	def _isi_kas(self):
		self.kas = False
		if self.starttanggal and self.endtanggal:
			hasilsearch = False
			if self.jenis == "kasbesar":
				hasilsearch = self.env['mmr.akundetil'].search([('idakun.nomorakun','=','1.1.02')])
			elif self.jenis == "kaskecil":
				hasilsearch = self.env['mmr.akundetil'].search([('idakun.nomorakun','=','1.1.01')])
			elif self.jenis == "kasbank":
				hasilsearch = self.env['mmr.akundetil'].search([('idakun.nomorakun','=','1.1.03.1')])
			elif self.jenis == "kaslab":
				hasilsearch = self.env['mmr.akundetil'].search([('idakun.nomorakun','=','1.1.04.2')])	 		 	
			nilai = 0
			akundetilid = {}
			if hasilsearch:
				for semuaakundetil in hasilsearch:
					tanggal = False
					if semuaakundetil.sumberpembelianfaktur:
						tanggal = semuaakundetil.sumberpembelianfaktur.tanggalterbit
					elif semuaakundetil.sumberpenjualanfaktur:
						tanggal = semuaakundetil.sumberpenjualanfaktur.tanggalterbit
					elif semuaakundetil.sumberpembayaranpembelian:
						tanggal = semuaakundetil.sumberpembayaranpembelian.tanggalbayar
					elif semuaakundetil.sumberpembayaranpenjualan:
						tanggal = semuaakundetil.sumberpembayaranpenjualan.tanggalbayar	
					elif semuaakundetil.sumberkegiatanakunting:
						tanggal = semuaakundetil.sumberkegiatanakunting.tanggal	
					elif semuaakundetil.sumberbiaya:
						tanggal = semuaakundetil.sumberbiaya.tanggal	
					elif semuaakundetil.sumberinventaris:
						tanggal = semuaakundetil.sumberinventaris.tanggal
					elif semuaakundetil.sumberjurnalpenyesuaian:
						tanggal = semuaakundetil.sumberjurnalpenyesuaian.tanggal
					elif semuaakundetil.sumberjurnalpenutup:
						tanggal = semuaakundetil.sumberjurnalpenutup.tanggal	
					elif semuaakundetil.sumberjurnalringkasan:
						tanggalperingkasan = "01" + semuaakundetil.sumberjurnalringkasan.bulan + semuaakundetil.sumberjurnalringkasan.tahun
						tanggal = datetime.datetime.strptime(tanggalperingkasan, "%d%m%Y").date()
					
					if tanggal >= self.starttanggal and tanggal <= self.endtanggal:
						if semuaakundetil.tanggal in akundetilid:
							akundetilid[tanggal] += semuaakundetil		
						else:
							akundetilid[tanggal] = semuaakundetil	
					if tanggal < self.starttanggal:
						nilai += semuaakundetil.debit
						nilai -= semuaakundetil.kredit
						
				akundetilidsorted = sorted(akundetilid.iterkeys())
				for semuaakundetilid in akundetilidsorted:
					for semuaakindetilid2 in akundetilid[semuaakundetilid]:
						self.kas+= self.env['mmr.akundetildummy'].new({'idcetakbackup' : self.id, 'tanggal' : semuaakundetilid,
																		'sumber' : semuaakindetilid2.sumber, 'debit' : semuaakindetilid2.debit,
																		'kredit': semuaakindetilid2.kredit})
				self.saldoawal = nilai	
	
	_columns = {
		'starttanggal' : fields.date("Start"),
		'endtanggal' : fields.date("End"),
		'jenis' : fields.selection([('pembelian','Pembelian'), ('penjualan','Penjualan'),
								 ('stok','Stok'),('kasbesar','Kas Besar'),('kaskecil','Kas Kecil'),
								 ('kaslab','Kas Lab'),('kasbank','Kas Bank'),('jurnal','Jurnal'),
								 ('kartuhutang','Kartu Hutang'),('bukubesar','Buku Besar')], "Jenis", required=True),
		'fakturbelidetil' : fields.one2many("mmr.stok","idcetakbackup","Faktur Beli Detil", compute="_isi_fakturbelidetil"),
		'fakturjualdetil' : fields.one2many("mmr.cetakfaktur","idcetakbackup","Faktur Beli Detil", compute="_isi_fakturjualdetil"),	
		'stok' : fields.one2many("mmr.laporanstok","idcetakbackup","Stok", compute="_isi_stok"),
		'kas' : fields.one2many("mmr.akundetildummy", "idcetakbackup", "Kas", compute="_isi_kas"),
		'saldoawal' : fields.float("SaldoAwal", digits=(12,2)),
	}	
	
mmr_cetakbackup()