from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools, api
import datetime
import itertools 

class mmr_pembelianpo(osv.osv):
    
    # Pembelian menjadi satu - satunya akses barang masuk
    # Prosedur Pembelian adalah membuat PO ( Biasa, Khusus, dan tukar barang )
    # Biasa, Setelah PO dibuat akan disetujui pihak otoritas, Barang dan Faktur dari supplier datang, input data seperti biasa, lakukan pembayaran
    # Khusus, apabila barang yang masuk sampel, ED Pendek, dll. Akan pengaruhi Stok, dimana stok nya akan diberi tanda barang khusus
    # stok dengan tanda khusus tidak dapat dikeluarkan secara otomatis, Tidak difaktur
    # Tukar Barang, Karena adanya CV Macro, gudang menjadi bercampur antara macro dan multi. Dimana gudang selalu menukar nukar barang multi dan macro
    # Untuk menukar barang perlu dilakukan dulu sebelumnya penjualan ke macro, baru pembelian ke macro dengan harga beli == harga beli barang yang dijual,
    # Tidak difaktur

    _name = "mmr.pembelianpo"
    _description = "Modul PO Pembelian untuk PT. MMR."
    _rec_name = "nomorpo"
    
    # PO Akan memiliki beberapa Surat Jalan dan beberapa Faktur
    # PO memiliki beberapa milestone hingga Surat Jalan dan Faktur! Tergambarakan pada status (Baru, Barang Belum Dikirim, dll.)
    def batal(self,cr,uid,ids,context=None):
        pembelianpoclass = self.pool.get("mmr.pembelianpo")
        pembelianpoobj = pembelianpoclass.browse(cr,uid,ids)
        
        # Apabila sudah datang barang / faktur / keduanya, PO tidak dapat lagi dibatalkan
        if len(pembelianpoobj.pembeliansj) > 0 or len(pembelianpoobj.pembelianfaktur) > 0:
            raise osv.except_osv(_('Tidak Dapat Dibatalkan'),_("Sudah ada SJ dan Faktur untuk PO ini!"))    
        else:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            pembelianpoclass.write(cr,uid,ids,{'disetujuibool' : True, 'disetujui':userobj.login, 'dibatalkan' : userobj.login})
            
        return True
        
    # Ubah Status PO dan catat nama pengirim PO    
    def telahdikirim(self, cr, uid, ids, context=None):
        pembelianpoclass = self.pool.get("mmr.pembelianpo")
        pembelianpoobj = pembelianpoclass.browse(cr,uid,ids)
        
        if pembelianpoobj.disetujuibool == True:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            pembelianpoclass.write(cr,uid,ids,{'dikirim' : userobj.login})
        else:
            raise osv.except_osv(_('Tidak Dapat Dikirim'),_("Wajib Disetujui Terlebih Dahulu!"))    
        
        return True
    
    def revisi(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'disetujuibool':False})
        
        return True
    
    def setuju(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'disetujuibool':True})
        
        return True
    
    # Normalnya Setuju hanya oleh otoritas, kecuali untuk tukar barang. 
    # Untuk itu, selain masalah harga beli, segi keamanan juga lebih baik apabila akunting ikut menyetujui adanya perpindahan barang 
    def setujugudang(self, cr, uid, ids, context=None):
        if self.browse(cr,uid,ids).setujuakunting != False:
            self.write(cr,uid,ids,{'disetujuibool':True})
        else:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Akunting wajib menyetujui penukaran barang"))    

        return True
    
    # Buka Floating window pembuatan Surat Jalan
    # Oper ID parent
    def buatsj(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','mmr_pembeliansj')])
        return {
                    'name': 'Surat Jalan Pembelian',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mmr.pembeliansj',
                    'context': "{'idpo': " +  str(ids[0]) + "}",
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    }
        
    # Buka Floating window pembuatan Surat Jalan
    # Oper ID parent        
    def buatfaktur(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','mmr_pembelianfaktur')])
        return {
                    'name': 'Faktur Pembelian',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mmr.pembelianfaktur',
                    'context': "{'idpo': " +  str(ids[0]) + "}",
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    }
    
    # Isi Nomor PO, dan syarat pembayaran secara otomatis bergantung supplier yang dipilih        
    def onchange_supplier(self,cr,uid,ids,supplier,waktu,tanpafaktur, tukarbarang ,context=None):
        hasil = {}
        supplierClass = self.pool.get("mmr.supplier")
        supplierobj = supplierClass.browse(cr,uid,supplier)
        
        hasil['syaratpembayaran'] = supplierobj.syaratpembayaran.id
        
        # Aturan Penomoran PO Pembelian : 
        #     - Per Supplier
        #    - Per Tahun
        #    - PO Khusus ( Tukar Barang, PO Tanpa faktur ) tidak perlu di beri nomor
        if supplier!= False and waktu!= False:
            sqlQuery = """
            SELECT ID
            FROM mmr_pembelianpo
            WHERE supplier = %s AND date_part('year', waktu) = %s AND tanpafaktur = %s AND tukarbarang = %s
            """% (supplier, waktu[0:4], tanpafaktur, tukarbarang)
            cr.execute(sqlQuery)
            hasilquery = cr.dictfetchall()
            
            if len(ids) == 0:
                hasil['nomorpo'] = str(supplierobj.kode) + "/" + waktu[0:4] + "/" + waktu[5:7] + "/" + waktu[8:10] + "/" + str(len(hasilquery)+1)
            else:
                if self.browse(cr,uid,ids).supplier.id == supplier and self.browse(cr,uid,ids).waktu[0:4] == waktu[0:4]:
                    hasil['nomorpo'] = str(supplierobj.kode) + "/" + waktu[0:4] + "/" + waktu[5:7] + "/" + waktu[8:10] + "/" + str(len(hasilquery))
                else:
                    hasil['nomorpo'] = str(supplierobj.kode) + "/" + waktu[0:4] + "/" + waktu[5:7] + "/" + waktu[8:10] + "/" + str(len(hasilquery)+1)
            if tanpafaktur:
                hasil['nomorpo'] = str(supplierobj.kode) + "/" + waktu[0:4] + "/" + waktu[5:7] + "/" + waktu[8:10] + "/Tanpa Nomor"
            
        return {'value': hasil}    
    
    # Isi milestone PO
    # Gunakan field.function, hanya untuk informasi
    def _set_status(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for pembelianpo in self.browse(cr,uid,ids):
            # Secara default
            res[pembelianpo.id] = "Baru"
            
            # Apakah field telah dikirim sudah diisi
            if pembelianpo.dikirim != False:    
                res[pembelianpo.id] = "Telah Dikirim"    
                
            # Cek seluruh podetil barang diterima == barang pesanan
            lengkap = True
            for pembelianpodetil in pembelianpo.pembelianpodetil:
                if pembelianpodetil.jumlah != pembelianpodetil.jumlahditerima:
                    lengkap = False
            
            if lengkap:
                res[pembelianpo.id] = "Barang Lengkap"
            else:
                if pembelianpo.tanggaldijanjikan != False and datetime.datetime.today() > datetime.datetime.strptime(pembelianpo.tanggaldijanjikan,'%Y-%m-%d') :
                    res[pembelianpo.id] = "Barang Terlambat"    
            
            # Apabila ada pembatalan                
            if pembelianpo.dibatalkan != False:
                res[pembelianpo.id] = "Batal"            
        return res
    
    # Milestone khusus faktur
    def _set_statusfaktur(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for pembelianpo in self.browse(cr,uid,ids):
            # Secara default
            res[pembelianpo.id] = "Belum ada SJ"
            listpembeliansj = []
            
            # Apabila semua SJ lengkap difaktur
            for semuapembeliansj in pembelianpo.pembeliansj:
                listpembeliansj.append(semuapembeliansj.id)
            if len(listpembeliansj) <= 0:
                res[pembelianpo.id] = "Belum ada SJ"    
            else:    
                for semuapembelianfaktur in pembelianpo.pembelianfaktur:
                    if semuapembelianfaktur.pembeliansj1.id in listpembeliansj:
                        listpembeliansj.remove(semuapembelianfaktur.pembeliansj1.id)     
                    if semuapembelianfaktur.pembeliansj2.id in listpembeliansj:
                        listpembeliansj.remove(semuapembelianfaktur.pembeliansj2.id)     
                    if semuapembelianfaktur.pembeliansj3.id in listpembeliansj:
                        listpembeliansj.remove(semuapembelianfaktur.pembeliansj3.id)     
                    if semuapembelianfaktur.pembeliansj4.id in listpembeliansj:
                        listpembeliansj.remove(semuapembelianfaktur.pembeliansj4.id)     
                    if semuapembelianfaktur.pembeliansj5.id in listpembeliansj:
                        listpembeliansj.remove(semuapembelianfaktur.pembeliansj5.id)                     
                if len(listpembeliansj) > 0:
                    res[pembelianpo.id] = "Faktur tidak lengkap"
                else:
                    res[pembelianpo.id] = "Faktur lengkap"
            
            # Apabila PO Pembelian digunakan untuk tukar barang / Tanpa Faktur
            if pembelianpo.tanpafaktur or pembelianpo.tukarbarang:    
                res[pembelianpo.id] = "Tanpa Faktur"
                            
        return res
    
    # PO Memiliki beberapa PO Detil ( Alias Tabel barang yang dipesan )
    # Harga per barang terdapat pada PO Detil, PO Hanya mentotal seluruh nilainya.
    # Dilakukan dengan compute agar perubahan on-the-fly
    @api.one
    @api.depends("pembelianpodetil")
    def _hitung_harga(self):
        self.bruto, self.diskon, self.hppembelian, self.pajak, self.netto = 0,0,0,0,0
        for semuapodetil in self.pembelianpodetil:
            self.bruto += semuapodetil.bruto
            self.diskon += semuapodetil.bruto - semuapodetil.hppembelian
            self.hppembelian += semuapodetil.hppembelian
            self.pajak += semuapodetil.netto - semuapodetil.hppembelian
            self.netto += semuapodetil.netto    
        
    _columns = {
        'nomorpo': fields.char("Nomor PO",required=True),
        'supplier': fields.many2one("mmr.supplier", "Supplier", required=True),
        'waktu' : fields.date("Tanggal Terbit",required=True),
        'status': fields.function(_set_status, type="char", method=True, string= "Status"),
        'statusfaktur': fields.function(_set_statusfaktur, type="char", method=True, string= "Status Faktur"),
        'syaratpembayaran' : fields.many2one("mmr.syaratpembayaran", "Syarat Pembayaran"),
        'tanggaldijanjikan': fields.date("Tanggal Dijanjikan"),
        'pembelianpodetil': fields.one2many("mmr.pembelianpodetil","idpo","List Barang"),
        'pembeliansj': fields.one2many("mmr.pembeliansj","idpo","List SJ"),
        'pembelianfaktur': fields.one2many("mmr.pembelianfaktur","idpo","List Faktur"),
        'bruto': fields.float("Bruto", compute="_hitung_harga", store=True, digits=(12,2)),
        'diskon': fields.float("Diskon", compute="_hitung_harga", store=True, digits=(12,2)),
        'hppembelian': fields.float("HPPembelian", compute="_hitung_harga", store=True, digits=(12,2)),
        'pajak': fields.float("Pajak", compute="_hitung_harga", store=True, digits=(12,2)),
        'netto': fields.float("Netto", compute="_hitung_harga", store=True, digits=(12,2)),
        'pokhusus' : fields.boolean("Stok Khusus"),
        'tanpafaktur' : fields.boolean("Surat Jalan Sementara"),
        'tukarbarang' : fields.boolean("Tukar Barang"),
        'notes' : fields.text("Notes"),
        'dibuat' : fields.char("Dibuat", readonly=True),
        'diedit' : fields.char("Diedit", readonly=True),
        'disetujui' : fields.char("Disetujui", readonly=True),
        'dikirim' : fields.char("Dikirim", readonly=True),
        'disetujuibool' : fields.boolean("Setuju"),
        'dibatalkan' : fields.char("Dibatalkan", readonly=True),
        'setujuakunting' : fields.boolean("Setuju akunting"),
    }    
    
    _defaults = {
                'waktu': lambda *a: datetime.datetime.today(),
                'status': "Baru",
                'tanggaldijanjikan': lambda *a: datetime.datetime.today() + datetime.timedelta(days=7),
                }
    
    def create(self,cr,uid,vals,context=None):
        id = super(mmr_pembelianpo,self).create(cr,uid,vals,context)
        hasil = {}
        objini = self.browse(cr,uid,id)
        
        # Beri Nama Pembuat / Harusnya bisa create_uid saja
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        hasil['dibuat'] = userobj.login
        
        # Beri Nama Penyetuju
        if objini.disetujuibool == True:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            hasil['disetujui'] = userobj.login
        else:
            hasil['disetujui'] = False
        
        hasil['status'] = 'baru'
        
        self.write(cr,uid,id,hasil)
        validasipo(self,cr,uid,id)
        return id

    def write(self, cr, uid, ids, vals, context=None):
        super(mmr_pembelianpo,self).write(cr, uid, ids, vals, context=context)
        hasil = {}
        objini = self.browse(cr,uid,ids)
        
        # Nama Pengedit, Jangan beri nama pengedit apabila yang diedit bukan bagian dari PO, eks: SJ, Faktur, Pembayaran
        if 'supplier' in vals or 'waktu' in vals or 'syaratpembayaran' in vals or 'tanggaldijanjikan' in vals or 'pembelianpodetil' in vals or 'notes' in vals or 'nomorpo' in vals:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            hasil['diedit'] = userobj.login
        
        # Beri Nama Penyetuju
        if 'disetujuibool' in vals:
            if objini.disetujuibool == True :
                userclass = self.pool.get("res.users")
                userobj = userclass.browse(cr,uid,uid)
                hasil['disetujui'] = userobj.login
            else:
                hasil['disetujui'] = False    
        
        pobaru = super(mmr_pembelianpo,self).write(cr, uid, ids, hasil, context=context)
        validasipo(self,cr,uid,ids) 
        return pobaru
    
    # Apabila sudah disetujui tidak dapat dihapus
    # Kecuali jika dihapus via Hapus Otomatis (ijindelete)
    def unlink(self, cr, uid, ids, context):
        ids=[ids]
        for id in ids:
            pembelianpoobj = self.browse(cr,uid,id)
            if (pembelianpoobj.disetujuibool == True) and 'ijindelete' not in context:
                raise osv.except_osv(_('Tidak Dapat Menghapus'),_("PO Pembelian Telah Disetujui / Dikirim!"))
            super(mmr_pembelianpo, self).unlink(cr, uid, id, context)
        return True
    
    # Jangan bisa diduplikat
    def copy(self, cr, uid, id, default=None, context=None):
           raise osv.except_osv(_('Tidak Dapat Duplikasi'), _('Dilarang melakukan duplikasi data PO Pembelian.'))
           return True
       
mmr_pembelianpo()    


class mmr_pembelianpodetil(osv.osv):
    
    # Tabel produk di PO
    
    _name = "mmr.pembelianpodetil"
    _description = "Modul PO Pembelian Detail untuk PT. MMR."
    
    # Jumlah barang diterima berdasarkan SJ yang masuk.
    @api.one
    @api.depends("idpo.pembeliansj")
    def _hitung_jumlahditerima(self):
        jumlah = 0
        for seluruhsjpembelian in self.idpo.pembeliansj:
            for seluruhsjpembeliandetil in seluruhsjpembelian.pembeliansjdetil:
                if seluruhsjpembeliandetil.produk == self:
                    jumlah+= seluruhsjpembeliandetil.debit
        self.jumlahditerima = jumlah    
    
    # Jika merk diganti, hapus pilihan produknya
    def onchange_merk(self,cr,uid,ids,context=None):
        hasil = {}
        hasil['namaproduk'] = False
        return {'value': hasil}
    
    # Ketika mengisi produk, langsung dapatkan harga sesuai dengan daftar harga beli!
    # Ambil yang paling baru, dan yang termasuk dalam tanggal efektif, dan jumlah pembelian masuk yang mana.
    def onchange_namaproduk(self,cr,uid,ids,namaproduk,supplier,waktu,jumlah,harga,diskon,pajak,context=None):
        hasil = {}
        produkclass = self.pool.get("mmr.produk")
        daftarhargasupplierclass = self.pool.get("mmr.daftarhargasupplier")
        daftarhargasupplierobj = daftarhargasupplierclass.browse(cr,uid,daftarhargasupplierclass.search(cr,uid,[('namaproduk','=',namaproduk),('supplier','=',supplier),('tanggalefektif',"<=",waktu)]))
        
        hasil['harga'] = False
        hasil['diskon'] = False
        waktuterbaru = 0
        jumlahbeliterbesar = 0
        for semuaharga in daftarhargasupplierobj:
            if semuaharga.tanggalefektif >= waktuterbaru and semuaharga.tanggalefektif <= waktu and jumlah > semuaharga.lebihdari and jumlahbeliterbesar <= semuaharga.lebihdari:
                waktuterbaru = semuaharga.tanggalefektif
                jumlahbeliterbesar = semuaharga.lebihdari
                hasil['harga'] = semuaharga.harga
                hasil['diskon'] = semuaharga.diskon
        hasil['bruto'] = round(jumlah * harga,2)
        hasil['hppembelian'] = round(jumlah * harga - (jumlah * harga * diskon / 100),2)
        hasil['netto'] = round(jumlah * harga - (jumlah * harga * diskon / 100) + (jumlah * harga - (jumlah * harga * diskon / 100)) * pajak / 100,2)
        
        return {'value': hasil}
    
    # Hitung total harga
    def onchange_harga(self,cr,uid,ids,jumlah,harga,diskon,pajak,context=None):
        hasil = {}
        print '----------------------------------'
        print round(2.675,2)
        hasil['bruto'] = round(jumlah * harga,2)
        hasil['hppembelian'] = round(jumlah * harga - (jumlah * harga * diskon / 100),2)
        hasil['netto'] = round(jumlah * harga - (jumlah * harga * diskon / 100) + (jumlah * harga - (jumlah * harga * diskon / 100)) * pajak / 100,2)
        return {'value': hasil}
    
    # Pada SJ, user tinggal memilih barang yang akan diterima berdasarkan PO.
    # Sehingga PO Detil harus dapat ditampilkan se-jelas mungkin
    # Jika Notes Kosong, isi dengan (-)
    def name_get(self,cr,uid,ids,context):
        res=[]
        for produk in self.browse(cr,uid,ids,context):
            if produk.notes != False:
                kalimatproduk = produk.merk.merk + " " + produk.namaproduk.namaproduk + " ( " + str(produk.jumlah) + " " + produk.satuan.satuan + ", Catatan: " + str(produk.notes) + " )" 
            else:
                kalimatproduk = produk.merk.merk + " " + produk.namaproduk.namaproduk + " ( " + str(produk.jumlah) + " " + produk.satuan.satuan + ", Catatan: " + "-" + " )" 
                
            res.append((produk.id,kalimatproduk))
        return res
        
    _columns = {
        'supplier': fields.many2one("mmr.supplier", "Supplier Pada PO", related="idpo.supplier", required=True),
        'waktu': fields.date("Waktu pada PO", related="idpo.waktu", required=True),
        'idpo': fields.many2one("mmr.pembelianpo", "Pembelian PO",ondelete='cascade'),
        'merk': fields.many2one("mmr.merk", "Merk", required=True),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk", required=True, domain="[('merk', '=', merk)]"),
        'satuan' : fields.many2one("mmr.satuan", "Satuan", related="namaproduk.satuan", readonly=True),
        'jumlah': fields.integer("Jumlah", required=True),
        'jumlahditerima' : fields.integer("Jumlah Diterima", compute="_hitung_jumlahditerima"),
        'harga': fields.float("Harga", required=True, digits=(12,2)),
        'bruto': fields.float("Bruto", digits=(12,2)),
        'diskon': fields.float("Diskon(%)", required=True, digits=(12,2)),
        'hppembelian': fields.float("HPPembelian", digits=(12,2)),
        'pajak': fields.float("Pajak(%)", required=True, digits=(12,2)),
        'netto': fields.float("Netto", digits=(12,2)),
        'notes' : fields.text("Notes"),
    }    
    
    _defaults = {
                'supplier' : lambda self, cr, uid, c: c.get('supplier', False),
                'waktu' : lambda self, cr, uid, c: c.get('waktu', False),
                'pajak': 10,
                }
    
mmr_pembelianpodetil()


class mmr_pembeliansj(osv.osv):
    
    # Modul Surat Jalan, Berhubungan dengan 1 PO. 
    # Memiliki tabel barang, dimana tabel tersebut = Stok Masuk
    
    _name = "mmr.pembeliansj"
    _description = "Modul SJ Pembelian untuk PT. MMR."
    _rec_name = "nomorsj"
        
    def save(self,cr,uid,ids,context=None):
        return True
    
    _columns = {
        'idpo' :fields.many2one("mmr.pembelianpo", "IDPO",required=True),    
        'nomorsj': fields.char("Nomor SJ"),
        'waktu' : fields.datetime("Waktu",required=True),
        'tanggalterbit' : fields.date("Tanggal Terbit", required=True),
        'gudang' : fields.many2one("mmr.gudang", "Gudang", required=True),
        'pembeliansjdetil': fields.one2many("mmr.stok","idpembeliansj","List Produk"),
        'notes' : fields.text("Notes"),
        'dibuat': fields.char("Dibuat", readonly=True),
        'diedit' : fields.char("Diedit", readonly=True),
        'disetujui' : fields.char("Disetujui", readonly=True),
    }    
    
    _defaults = {
                'idpo' : lambda self, cr, uid, c: c.get('idpo', False),
                'waktu': lambda *a: datetime.datetime.today(),
                }
    
    def create(self,cr,uid,vals,context=None):
        id = super(mmr_pembeliansj,self).create(cr,uid,vals,context)
        objini = self.browse(cr,uid,id)
        hasil = {}
        
        # Simpan pembuat
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        hasil['dibuat'] = userobj.login
            
        self.write(cr,uid,id,hasil)    
        validasisj(self,cr,uid,id)
        return id
    
    def write(self,cr,uid,id,vals,context=None):
        res = super(mmr_pembeliansj,self).write(cr,uid,id,vals,context)
        # Simpan pengedit, jangan dianggap ada pengeditan apabila yang diubah tidak berhubungan dgn SJ
        if 'nomorsj' in vals or 'waktu' in vals or 'tanggalterbit' in vals or 'gudang' in vals or 'pembeliansjdetil' in vals or 'notes' in vals:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            vals['diedit'] = userobj.login
                
        res = super(mmr_pembeliansj,self).write(cr,uid,id,vals,context)
        validasisj(self,cr,uid,id)
        return res
    
    # Jangan bisa didelete apabila sudah disetujui / apabila PO belum disetujui
    def unlink(self, cr, uid, id, context):
        pembeliansj = self.browse(cr,uid,id)
        if pembeliansj.disetujui != False and 'ijindelete' not in context:
            raise osv.except_osv(_('Tidak Dapat Menghapus'),_("SJ Telah Disetujui!"))
        if pembeliansj.idpo.disetujui == False and 'ijindelete' not in context:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("PO Belum Disetujui"))    
        return super(mmr_pembeliansj, self).unlink(cr, uid, id, context)
       
mmr_pembeliansj()    

class mmr_pembelianfaktur(osv.osv):
    
    # Faktur PO memiliki beberapa SJ ( Sebagai pengaman apabila ada supplier yang meminta demikian , Max 5 )
    
    _name = "mmr.pembelianfaktur"
    _description = "Modul Faktur Pembelian untuk PT. MMR."
    _rec_name = "nomorfaktur"
    
    
    def save(self, cr, uid, ids, context):
        return True
    
    # Setujui Faktur, sekali disetujui tidak dapat diedit
    # Begitu faktur disetujui, SJ yang difaktur Ikut dikunci.
    def setuju(self, cr, uid, ids, context):
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        self.write(cr,uid,ids,{'disetujui':userobj.login})
                            
        pembeliansjClass = self.pool.get("mmr.pembeliansj")
        objini = self.browse(cr,uid,ids)
        if objini.pembeliansj1 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj1.id,{'disetujui':userobj.login})        
        if objini.pembeliansj2 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj2.id,{'disetujui':userobj.login})    
        if objini.pembeliansj3 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj3.id,{'disetujui':userobj.login})    
        if objini.pembeliansj4 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj4.id,{'disetujui':userobj.login})    
        if objini.pembeliansj5 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj5.id,{'disetujui':userobj.login})    
                                    
        return { 'type': 'ir.actions.client',
            'tag': 'reload'}
    
    def revisi(self, cr, uid, ids, context):
        self.write(cr,uid,ids,{'disetujui':False})
                            
        pembeliansjClass = self.pool.get("mmr.pembeliansj")
        objini = self.browse(cr,uid,ids)
        if objini.pembeliansj1 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj1.id,{'disetujui':False})        
        if objini.pembeliansj2 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj2.id,{'disetujui':False})    
        if objini.pembeliansj3 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj3.id,{'disetujui':False})    
        if objini.pembeliansj4 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj4.id,{'disetujui':False})    
        if objini.pembeliansj5 != False:
            pembeliansjClass.write(cr,uid,objini.pembeliansj5.id,{'disetujui':False})    
        
        return { 'type': 'ir.actions.client',
            'tag': 'reload' }
    
    # Otomatis hitung harga berdasarkan SJ yang dipilih. SJ Memiliki hubungan harga dengan PO.
    # Sehingga nilai faktur akan sama dengan nilai PO. 
    @api.one
    @api.depends("pembeliansj1.pembeliansjdetil", "pembeliansj2.pembeliansjdetil", "pembeliansj3.pembeliansjdetil"
                ,"pembeliansj4.pembeliansjdetil", "pembeliansj5.pembeliansjdetil", "biayalain", "idpo.pembelianpodetil")
    def _hitung_harga(self):
        bruto, diskon, hpp, pajak, netto = 0,0,0,0,0
        listdarilistproduk = [self.pembeliansj1, self.pembeliansj2, self.pembeliansj3, self.pembeliansj4, self.pembeliansj5]
        for listproduk in listdarilistproduk:
            for produk in listproduk.pembeliansjdetil:
                 bruto+= produk.bruto
                 diskon+= produk.bruto - produk.hppembelian
                 hpp+= produk.hppembelian
                 pajak+= produk.netto - produk.hppembelian
                 netto+= produk.netto
        self.bruto = bruto    
        self.diskon = diskon    
        self.hppembelian = hpp    
        self.pajak = pajak    
        self.netto = netto + self.biayalain    
    
    # Isi tampilan barang secara otomatis berdasarkan SJ yang difakturkan
    # Agar on-the-fly gunakan compute
    @api.one
    @api.depends("pembeliansj1.pembeliansjdetil","pembeliansj2.pembeliansjdetil",
                "pembeliansj3.pembeliansjdetil","pembeliansj4.pembeliansjdetil","pembeliansj5.pembeliansjdetil",
                "idpo.pembelianpodetil")    
    def _isi_barang(self):
        sj = [self.pembeliansj1,self.pembeliansj2,self.pembeliansj3,self.pembeliansj4,self.pembeliansj5]
        self.pembelianfakturdetil = False
        for semuasj in sj:
            if semuasj.id != False:
                for semuaproduksj in semuasj.pembeliansjdetil:
                    self.pembelianfakturdetil += semuaproduksj
    
    #Berdasarkan tanggal terbit, tentukan jatuh tempo ( Berdasar waktu lama bayar supplier )    
    def onchange_tanggalterbit(self,cr,uid,ids,idpo,tanggalterbit,context=None):
        hasil ={}
        if tanggalterbit!=False:
            tanggalterbit = datetime.datetime.strptime(tanggalterbit,"%Y-%m-%d")
            pembelianpoClass = self.pool.get("mmr.pembelianpo")
            pembelianpoobj = pembelianpoClass.browse(cr,uid,idpo)
            hasil['jatuhtempo'] = tanggalterbit + datetime.timedelta(days = pembelianpoobj.syaratpembayaran.lama)
        return {'value': hasil}        
    
    # Isi Akun otomatis, berdasarkan aturan yang dipilih, agak repot karena harus menciptakan one2many baru dan harus on-the-fly
    # Sehingga hanya gunakan on_change ( Depends tidak bisa pakai new ) dan apabila create, akan error looping
    # Method ini hanya menambahkan jurnal, nilainya akan diambil otomatis dari kelas jurnal sendiri, berdasarkan sumber jurnal
    # Apabila terjadi perubahan aturan akun, write pada aturan akun telah diisi agar merubah seluruh jurnal-nya 
    @api.one
    @api.onchange("pembeliansj1","pembeliansj2","pembeliansj3","pembeliansj4","pembeliansj5",
                "aturanakun","akunotomatis","biayalain")
    def _isi_akun(self):
        if self.netto!=False and self.aturanakun!=False and self.akunotomatis != False:
            data= {'bruto':self.bruto,'diskon':self.diskon,'pajak':self.pajak,'biayalain':self.biayalain,'netto':self.netto,
                'hppembelian' : self.hppembelian}
            self.akunterkena = False
            
            for semuaakundetil in self.aturanakun.aturanakundetil:
                if semuaakundetil.debitkredit =="debit":
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id,"tanggal":self.tanggalterbit, "kredit": 0,
                                                                "debit": data[semuaakundetil.field.name], "sumberpembelianfaktur": self.id, "notes": False})
                else:
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id,"tanggal":self.tanggalterbit, "kredit": 0,
                                                                "kredit": data[semuaakundetil.field.name], "sumberpembelianfaktur": self.id, "notes": False})
        return self
    
    def _set_status(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        res = {}
        # Jangan lakukan apapun apabila anda bukan anggota yang diijinkan, sehingga tidak melanggar 
        # permisiion pada grup
        grupClass = self.pool.get("res.groups")
        grupobj = grupClass.search(cr,uid,[('name','=','Akunting')])
        userClass = self.pool.get("res.users")
        grupditemukan = False
        for semuagrup in userClass.browse(cr,uid,uid).groups_id:
            if semuagrup.id == grupobj[0]:
                grupditemukan = True
        
        pembayaranpembeliandetilClass = self.pool.get("mmr.pembayaranpembeliandetil")
        if grupditemukan:
            for pembelianfaktur in self.browse(cr,uid,ids):
                # 1. Selalu set belum lunas
                res[pembelianfaktur.id]    = "Belum Lunas"
                
                # 2. Cek pembayaran, antara cicil --> ada pembayaran tp tidak membuat lunas, lunas --> Sudah tidak hutang    
                hasilsearch = pembayaranpembeliandetilClass.search(cr,uid,[("idfakturpembelian","=",pembelianfaktur.id)])
                total = 0
                for semuahasilsearch in hasilsearch:
                    pembayaranpembeliandetilobj = pembayaranpembeliandetilClass.browse(cr,uid,semuahasilsearch)
                    total += pembayaranpembeliandetilobj.bayar
                if total > 0 and total < pembelianfaktur.netto:
                    res[pembelianfaktur.id]    = "Cicil"
                elif total == pembelianfaktur.netto:
                    res[pembelianfaktur.id] = "Lunas"
                if pembelianfaktur.lunas:
                    res[pembelianfaktur.id] = "Lunas"
                
                # 3. Warning --> pembayaran belum beres walau sudah lewat jatuh tempo    
                if datetime.datetime.today() > datetime.datetime.strptime(pembelianfaktur.jatuhtempo,'%Y-%m-%d') and res[pembelianfaktur.id] != "Lunas":
                    res[pembelianfaktur.id] = "Warning"
                
                # 4. Jurnal tidak balance --> Kalau jurnal tidak imbang debit kreditnya        
                total = 0
                for semuaakundetil in pembelianfaktur.akunterkena:
                    total+=semuaakundetil.debit
                    total-=semuaakundetil.kredit
                if round(total,2)!=0:
                    res[pembelianfaktur.id]    = "Jurnal Tidak Balance"
                    
        return res
    
    # Isi total pembayaran untuk faktur ini
    # Sifatnya hanya informasi
    def _isi_totalbayar(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        res = {}
        for pembelianfaktur in self.browse(cr,uid,ids):
            res[pembelianfaktur.id] = 0
            for semuapembayaran in pembelianfaktur.listpembayaran:
                res[pembelianfaktur.id] += semuapembayaran.bayar
            if pembelianfaktur.lunas:
                res[pembelianfaktur.id] = pembelianfaktur.netto            
        return res
    
    # Baca status kelunasan
    # Harus up-to-date agar faktur yang dipilih untuk dibayar dapat lgsg dibatasi oleh status kelunasannya
    @api.one
    @api.depends("netto","listpembayaran","listpembayaran.bayar","setlunas")
    def _set_lunas(self):
        total = 0
        for semualistbayar in self.listpembayaran:
            total += semualistbayar.bayar
        if round(total,2) == round(self.netto,2):
            self.lunas = True
        else:
            self.lunas = False
        if self.setlunas:
            self.lunas = True    
        
        
    _columns = {
        'idpo' :fields.many2one("mmr.pembelianpo", "IDPO", required=True),    
        'supplier' : fields.many2one("mmr.supplier", "supplier", related="idpo.supplier",required=True),
        'nomorfaktur': fields.char("Nomor Faktur"),
        'nofakturpajak' : fields.char("Nomor Faktur Pajak"),
        'waktu' : fields.datetime("Waktu",required=True),
        'status' : fields.function(_set_status,type="char",method=True,string="Status"),
        'lunas' : fields.boolean("Lunas",compute="_set_lunas"),
        'jatuhtempo': fields.date("Jatuh Tempo",required=True),
        'tanggalterbit' : fields.date("Tanggal Terbit", required=True),
        'totalbayar' : fields.function(_isi_totalbayar,type="float",method=True,string="Total Pembayaran", digits=(12,2)),
        'setlunas' : fields.boolean("Lunas",help="Apabila pembelian dilakukan secara tunai, dan faktur langsung lunas, centang tombol ini!"),
        
        #------------------------------------------------------------------------------
        'pembeliansj1' : fields.many2one("mmr.pembeliansj", "Surat Jalan(1)", domain="[('idpo', '=', idpo),('id', '!=', pembeliansj2),('id', '!=', pembeliansj3),('id', '!=', pembeliansj4),('id', '!=', pembeliansj5)]", required=True),
        'pembeliansj2' : fields.many2one("mmr.pembeliansj", "Surat Jalan(2)", domain="[('idpo', '=', idpo),('id', '!=', pembeliansj1),('id', '!=', pembeliansj3),('id', '!=', pembeliansj4),('id', '!=', pembeliansj5)]"),
        'pembeliansj3' : fields.many2one("mmr.pembeliansj", "Surat Jalan(3)", domain="[('idpo', '=', idpo),('id', '!=', pembeliansj1),('id', '!=', pembeliansj2),('id', '!=', pembeliansj4),('id', '!=', pembeliansj5)]"),
        'pembeliansj4' : fields.many2one("mmr.pembeliansj", "Surat Jalan(4)", domain="[('idpo', '=', idpo),('id', '!=', pembeliansj1),('id', '!=', pembeliansj2),('id', '!=', pembeliansj3),('id', '!=', pembeliansj5)]"),
        'pembeliansj5' : fields.many2one("mmr.pembeliansj", "Surat Jalan(5)", domain="[('idpo', '=', idpo),('id', '!=', pembeliansj1),('id', '!=', pembeliansj2),('id', '!=', pembeliansj3),('id', '!=', pembeliansj4)]"),
        'pembelianfakturdetil' : fields.one2many("mmr.stok", "idpembelianfaktur", "ListBarang",compute="_isi_barang"),
        #-------------------------------------------------------------------------------
        
        'aturanakun' : fields.many2one("mmr.aturanakun", "Aturan Jurnal", required=True, domain="[('model', '=', namamodel)]"),
        'akunterkena' : fields.one2many("mmr.akundetil","sumberpembelianfaktur","Akuntansi"),
        'listpembayaran' : fields.one2many("mmr.pembayaranpembeliandetil","idfakturpembelian","List Pembayaran"),
        'trigger' : fields.char("Trigger",compute="_isi_akun"),
        'bruto' : fields.float("Bruto", compute="_hitung_harga", digits=(12,2)),
        'diskon' : fields.float("Diskon", compute="_hitung_harga", digits=(12,2)),
        'hppembelian' : fields.float("HPPembelian", compute="_hitung_harga", digits=(12,2)),
        'pajak' : fields.float("Pajak", compute="_hitung_harga", digits=(12,2)),
        'biayalain' : fields.float("Biaya Lain", digits=(12,2)),
        'netto' : fields.float("Netto", compute="_hitung_harga", digits=(12,2)),
        'notes' : fields.text("Notes"),
        'dibuat': fields.char("Dibuat", readonly=True),
        'diedit': fields.char("Diedit", readonly=True),
        'disetujui' : fields.char("Disetujui", readonly=True),
        'disetujuibool' : fields.boolean("Setuju"),
        'akunotomatis': fields.boolean("Otomatisasi Jurnal", help="Apabila tercentang, jurnal akan diisi otomatis sesuai data yang ada! Sebaliknya, jurnal tidak akan diisi otomatis dan user dapat mengubah jurnal secara manual!"),
        'namamodel' : fields.char("NamaModel"),
    }    
    
    _defaults = {
                'idpo' : lambda self, cr, uid, c: c.get('idpo', False),
                'waktu': lambda *a: datetime.datetime.today(),
                'akunotomatis': True,
                'status': "Belum Lunas",
                'namamodel' : "mmr.pembelianfaktur",
                'lunas' : False
                }
    
    def create(self,cr,uid,vals,context=None):
        id = super(mmr_pembelianfaktur,self).create(cr,uid,vals,context)
        objini = self.browse(cr,uid,id)
        hasil = {}
        
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        hasil['dibuat'] = userobj.login
        
        self.write(cr,uid,id,hasil)    
        validasifaktur(self,cr,uid,id)
        return id
    
    def write(self,cr,uid,id,vals,context=None):
        res = super(mmr_pembelianfaktur,self).write(cr,uid,id,vals,context)
        objini = self.browse(cr,uid,id)
        hasil = {}
        
        # Isi pengedit, jangan isi apabila tidak mengedit faktur
        if 'nomorfaktur' in vals or 'waktu' in vals or 'jatuhtempo' in vals or 'tanggalterbit' in vals or 'pembeliansj1' in vals or 'pembeliansj2' in vals or 'pembeliansj3' in vals or 'pembeliansj4' in vals or 'pembeliansj5' in vals or 'akunterkenashow' in vals or 'biayalain' in vals or 'notes' in vals or 'akunotomatis' in vals:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            hasil['diedit'] = userobj.login
                
        res = super(mmr_pembelianfaktur,self).write(cr,uid,id,hasil,context)
        validasifaktur(self,cr,uid,id)
        return res
    
    # Jangan bisa dihapus apabila sudah disetujui / faktur belum disetujui kecuali pakai auto delete
    def unlink(self, cr, uid, id, context):
        pembelianfaktur = self.browse(cr,uid,id)
        if pembelianfaktur.disetujui != False and 'ijindelete' not in context:
            raise osv.except_osv(_('Tidak Dapat Menghapus'),_("Faktur Telah Disetujui!"))
        if pembelianfaktur.idpo.disetujui == False and 'ijindelete' not in context:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("PO Belum Disetujui"))    
        return super(mmr_pembelianfaktur, self).unlink(cr, uid, id, context)
    
mmr_pembelianfaktur()

def validasipo(self,cr,uid,id,context=None):
    hasil={}
    listbarang = {}
    # PODETIL---------------------------------
    # 
    # 1. Pastikan merk, namaproduk, satuan cocok!
    #      Browse diri sendiri, iterasi ke semua PODetilnya, ambil id barangnya, browse barang tersebut, cocokkan merk dan satuan dari hasil browse dengan dari podetil
    # 2. Pastikan barang tidak ada yang kembar kecuali memiliki harga berbeda / keterangan berbeda
    # 3. Sekaligus catat sebagai dasar cek SJ
    
    objini = self.browse(cr,uid,id)
    produkclass = self.pool.get("mmr.produk")
    
    for semuabarang in objini.pembelianpodetil:
        listbarang[semuabarang.id] = semuabarang.jumlah
        produkini = produkclass.browse(cr,uid,semuabarang.namaproduk.id)
        if produkini.merk.id != semuabarang.merk.id or produkini.satuan.id != semuabarang.satuan.id:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Produk tidak terdaftar!"))
        
    # SJ----------------------------------------------------------
    # 
    # 1. Pastikan barang yang ada di SJ tepat dan tidak melebihi yang dipesan, sudah ada di validasi SJ, tetapi apabila yang diedit adalah POnya!
    #     Browse seluruh SJ, ambil tiap SJDetilnya, masukkan ke list, Cek Adanya, dan Cek Jumlahnya
    
    for semuaSJ in objini.pembeliansj:
        for semuaSJDetil in semuaSJ.pembeliansjdetil:
            if semuaSJDetil.produk.id in listbarang:
                listbarang[semuaSJDetil.produk.id]    -= semuaSJDetil.debit
            else:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Produk Pesanan Dan SJ Tidak Sesuai!"))
            
            if listbarang[semuaSJDetil.produk.id] < 0:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Produk Yang Diterima Lebih Banyak Dari Pesanan!"))
    
    # PO--------------------------------------------------------------
    # Pastikan totalnya tidak akan melebihi batas hutang ke supplier ini.
    supplierClass = self.pool.get("mmr.supplier")
    pembayaranpembelianClass = self.pool.get("mmr.pembayaranpembelian")
    supplierobj = supplierClass.browse(cr,uid,objini.supplier.id)
    # Hitung Total Hutang, Cari Seluruh PO dengan supplier ini
    # Ambil seluruh fakturnya, jumlahkan nettonya
    # Ambil seluruh pembayaran dari supplier ini, kurangkan jumlah dengan bayar
    total = 0
    for semuapo in self.browse(cr,uid,self.search(cr,uid,[('supplier','=',objini.supplier.id)])):
        for semuafaktur in semuapo.pembelianfaktur:
            total+=semuafaktur.netto
    for semuapembayaran in pembayaranpembelianClass.search(cr,uid,[('supplier','=',objini.supplier.id)]):
        total-= pembayaranpembelianClass.browse(cr,uid,semuapembayaran).bayar
        
    if total > supplierobj.batashutang:
        raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Melebihi Batas Hutang Kepada Supplier!"))
    
    if objini.tukarbarang and objini.supplier.nama != "Macrocitra Multicheck":
         raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Tukar Barang hanya bisa dengan Macrocitra Multicheck!"))            
    return True

def validasisj(self,cr,uid,id,context=None):
    hasil={}
    listproduk = {}
    objini = self.browse(cr,uid,id)
    # SJDETIL---------------------------------
    # 1. Pastikan jumlah yang ada di SJ tidak melebihi pesanan, dan barang tersebut ada di SJ!
    #    Browse diri sendiri, buat list ['nopodetil' : 'jumlahpesanan'], Iterasi seluruh sj, tiap Detil dengan produk sama mengurangi jumlah ke list.
    
    for semuaprodukpo in objini.idpo.pembelianpodetil:
        listproduk[semuaprodukpo] = semuaprodukpo.jumlah
    for semuasj in objini.idpo.pembeliansj:
        for semuasjdetil in semuasj.pembeliansjdetil:
            if semuasjdetil.produk in listproduk:
                listproduk[semuasjdetil.produk] -= semuasjdetil.debit
            else:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Produk tidak terdaftar!"))    
    for semuaproduk in listproduk:
        if listproduk[semuaproduk] < 0:
            notes = ""
            if semuaproduk.notes != False:
                notes = str(semuaproduk.notes)
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Jumlah Produk: " + semuaproduk.merk.merk + " " + semuaproduk.namaproduk.namaproduk + " " + notes + " Melebihi Yang Dibeli" + " (Pesan:" + str(semuaproduk.jumlah) + ", Datang:" + str(semuaproduk.jumlah - listproduk[semuaproduk]) + ")"))    
    # 2. Pastikan Stok Keluar tidak melebihi stok masuk
        for semuapembeliansjdetil in objini.pembeliansjdetil:
            if semuapembeliansjdetil.debit < semuapembeliansjdetil.kredit:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Barang Keluar lebih Banyak dari yang Masuk"))    

    return True

def validasifaktur(self,cr,uid,id,context=None):
    objini = self.browse(cr,uid,id)
    # Cek SJ kembar di faktur
    listsj = []
    for semuafaktur in objini.idpo.pembelianfaktur:
        if semuafaktur.pembeliansj1 in listsj and semuafaktur.pembeliansj1.nomorsj != False:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Sudah Ada Faktur dengan Surat Jalan: "+ str(semuafaktur.pembeliansj1.nomorsj)))    
        else:
            listsj.append(semuafaktur.pembeliansj1)
        if semuafaktur.pembeliansj2 in listsj and semuafaktur.pembeliansj2.nomorsj != False:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Sudah Ada Faktur dengan Surat Jalan: "+ str(semuafaktur.pembeliansj2.nomorsj)))    
        else:
            listsj.append(semuafaktur.pembeliansj2)
        if semuafaktur.pembeliansj3 in listsj and semuafaktur.pembeliansj3.nomorsj != False:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Sudah Ada Faktur dengan Surat Jalan: "+ str(semuafaktur.pembeliansj3.nomorsj)))    
        else:
            listsj.append(semuafaktur.pembeliansj3)
        if semuafaktur.pembeliansj4 in listsj and semuafaktur.pembeliansj4.nomorsj != False:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Sudah Ada Faktur dengan Surat Jalan: "+ str(semuafaktur.pembeliansj4.nomorsj)))    
        else:
            listsj.append(semuafaktur.pembeliansj4)
        if semuafaktur.pembeliansj5 in listsj and semuafaktur.pembeliansj5.nomorsj != False:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Sudah Ada Faktur dengan Surat Jalan: "+ str(semuafaktur.pembeliansj5.nomorsj)))    
        else:
            listsj.append(semuafaktur.pembeliansj5)    
            
    return True                


    