from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools, api
from dateutil.relativedelta import relativedelta
import datetime
import itertools 

class mmr_gudang(osv.osv):
    
    # Memiliki fitur menghitung jumlah barang di gudang dan nilainya ( Untuk akunting )
    
    _name = "mmr.gudang"
    _description = "Modul gudang untuk PT. MMR."
    _rec_name = "nama"
    
    def _hitung_jumlah(self, cr, uid, ids, field_name, arg, context):
        res = {}
        sjpembelianClass = self.pool.get("mmr.pembeliansj")
        stokkeluarClass = self.pool.get("mmr.stokkeluar")
        # Cari seluruh pembelian pada suatu gudang, jumlahkan total pembeliannya ( Stok )
        # Kurangi dengan jumlah pada stok keluar
        for gudang in self.browse(cr,uid,ids):
            sjpembelianobj = sjpembelianClass.browse(cr,uid,sjpembelianClass.search(cr,uid,[('gudang','=',gudang.id)]))
            jumlah = 0
            for seluruhsjpembelian in sjpembelianobj:
                for seluruhsjpembeliandetil in seluruhsjpembelian.pembeliansjdetil:
                    jumlah+= seluruhsjpembeliandetil.debit
            stokkeluarobj = stokkeluarClass.browse(cr,uid,stokkeluarClass.search(cr,uid,[('gudang','=',gudang.id)]))
            for seluruhstokkeluar in stokkeluarobj:
                jumlah -= seluruhstokkeluar.jumlah
            res[gudang.id] = jumlah    
            
        return res
    
    def _hitung_nilai(self, cr, uid, ids, field_name, arg, context):
        res = {}
        sjpembelianClass = self.pool.get("mmr.pembeliansj")
        stokkeluarClass = self.pool.get("mmr.stokkeluar")
        # Cari seluruh pembelian pada suatu gudang, jumlahkan total pembeliannya ( Stok ) dikali dengan HPP
        # Kurangi dengan jumlah pada stok keluar dikali HPP
        for gudang in self.browse(cr,uid,ids):
            sjpembelianobj = sjpembelianClass.browse(cr,uid,sjpembelianClass.search(cr,uid,[('gudang','=',gudang.id)]))
            jumlah = 0
            for seluruhsjpembelian in sjpembelianobj:
                for seluruhsjpembeliandetil in seluruhsjpembelian.pembeliansjdetil:
                    jumlah+= round((seluruhsjpembeliandetil.debit * seluruhsjpembeliandetil.produk.harga),2) - round((seluruhsjpembeliandetil.debit * seluruhsjpembeliandetil.produk.harga * seluruhsjpembeliandetil.produk.diskon / 100),2)
            stokkeluarobj = stokkeluarClass.browse(cr,uid,stokkeluarClass.search(cr,uid,[('gudang','=',gudang.id)]))
            for seluruhstokkeluar in stokkeluarobj:
                jumlah -= round((seluruhstokkeluar.idstok.produk.harga * seluruhstokkeluar.jumlah),2) - round((seluruhstokkeluar.idstok.produk.harga * seluruhstokkeluar.jumlah* seluruhstokkeluar.idstok.produk.diskon / 100),2) 
            res[gudang.id] = jumlah    
            
        return res
    
    # Untuk keperluan akunting, gudang juga dapat dilihat nilainya per bulan yang diminta
    @api.one
    @api.depends("bulan","tahun")
    def _hitung_nilai_bulan(self):
        self.nilaibulan = 0
        if self.bulan and self.tahun:
            sjpembelianClass = self.env["mmr.pembeliansj"]
            stokkeluarClass = self.env["mmr.stokkeluar"]
            sjpembelianobj = sjpembelianClass.search([('gudang','=',self.search([('nama','=',self.nama)]).id)])
            jumlah = 0
            listproduk = {}
            for seluruhsjpembelian in sjpembelianobj:
                bulantahun = seluruhsjpembelian.tanggalterbit[0:4] + seluruhsjpembelian.tanggalterbit[5:7]
                if bulantahun <= self.tahun + self.bulan:
                    for seluruhsjpembeliandetil in seluruhsjpembelian.pembeliansjdetil:
                        jumlah+= round((seluruhsjpembeliandetil.debit * seluruhsjpembeliandetil.produk.harga),2) - round((seluruhsjpembeliandetil.debit * seluruhsjpembeliandetil.produk.harga * seluruhsjpembeliandetil.produk.diskon / 100),2)
                        if seluruhsjpembeliandetil.namaproduk.namaproduk in listproduk:
                            listproduk[seluruhsjpembeliandetil.namaproduk.namaproduk] += round((seluruhsjpembeliandetil.debit * seluruhsjpembeliandetil.produk.harga),2) - round((seluruhsjpembeliandetil.debit * seluruhsjpembeliandetil.produk.harga * seluruhsjpembeliandetil.produk.diskon / 100),2)
                        else:
                            listproduk[seluruhsjpembeliandetil.namaproduk.namaproduk] = round((seluruhsjpembeliandetil.debit * seluruhsjpembeliandetil.produk.harga),2) - round((seluruhsjpembeliandetil.debit * seluruhsjpembeliandetil.produk.harga * seluruhsjpembeliandetil.produk.diskon / 100),2)
            stokkeluarobj = stokkeluarClass.search([('gudang','=',self.search([('nama','=',self.nama)]).id)])
            for seluruhstokkeluar in stokkeluarobj:
                bulantahun = seluruhstokkeluar.tanggal[0:4] + seluruhstokkeluar.tanggal[5:7]
                if bulantahun <= self.tahun + self.bulan:
                    jumlah -= round((seluruhstokkeluar.idstok.produk.harga * seluruhstokkeluar.jumlah),2) - round((seluruhstokkeluar.idstok.produk.harga * seluruhstokkeluar.jumlah* seluruhstokkeluar.idstok.produk.diskon / 100),2) 
                    if seluruhstokkeluar.namaproduk.namaproduk in listproduk:
                            listproduk[seluruhstokkeluar.namaproduk.namaproduk] -= round((seluruhstokkeluar.idstok.produk.harga * seluruhstokkeluar.jumlah),2) - round((seluruhstokkeluar.idstok.produk.harga * seluruhstokkeluar.jumlah* seluruhstokkeluar.idstok.produk.diskon / 100),2) 
            self.nilaibulan = jumlah
        
    _columns = {
        'nama': fields.char("Nama", required=True),
        'alamat': fields.char("Alamat"),
        'telp': fields.char("Telepon"),
        'jumlah': fields.function(_hitung_jumlah, type="float", method=True, string="Jumlah", digits=(12,2)),
        'nilai': fields.function(_hitung_nilai, type="float", method=True, string="Nilai", digits=(12,2)),
        'bulan' : fields.selection([('01','Januari'), ('02','Februari'), ('03','Maret')
                                    , ('04','April'), ('05','Mei'), ('06','Juni'), ('07','Juli')
                                    , ('08','Agustus'), ('09','September'), ('10','Oktober'), ('11','November')
                                    , ('12','Desember')], "Bulan"),
        'tahun' : fields.selection([('2015','2015'), ('2016','2016'), ('2017','2017')
                                    , ('2018','2018'), ('2019','2019'), ('2020','2020'), ('2021','2021')
                                    , ('2022','2022'), ('2023','2023'), ('2024','2024'), ('2025','2025')], "Tahun"),
        'nilaibulan' : fields.float("Nilai bulan dipilih", compute="_hitung_nilai_bulan", digits=(12,2)),
        'notes' : fields.text("Notes"),
    }    
    
    _sql_constraints = [
        ('name_uniq', 'unique(nama)', 'Gudang Sudah Ada!')
    ]
    
    def create(self,cr,uid,vals,context=None):
        vals['bulan'] = False
        vals['tahun'] = False
        id = super(mmr_gudang,self).create(cr,uid,vals,context)
        return id
    
    def write(self,cr,uid,ids,vals,context=None):
        vals['bulan'] = False
        vals['tahun'] = False
        return super(mmr_gudang,self).write(cr, uid, ids, vals, context=context)
    
mmr_gudang()

# Stok "diinput" langsung oleh user ketika membuat SJ Pembelian
# Setiap barang masuk ketika PO == Stok. Didalam stok terdapat stok keluar.
class mmr_stok(osv.osv):
    _name = "mmr.stok"
    _description = "Modul Stok untuk PT. MMR."
    
    # Agar User dapat memilih stok dengan mudah, informasi pada pilihan dibuat selengkap mungkin
    def name_get(self,cr,uid,ids,context):
        res=[]
        for stok in self.browse(cr,uid,ids,context):
            kadaluarsa = "-"
            if stok.kadaluarsa:
                kadaluarsa = stok.kadaluarsa
            lot = "-"
            if stok.lot:
                lot = stok.lot
            brgpinjam = "-"
            if stok.stokkhusus:
                brgpinjam = "Brg Pinjaman"
                    
            kalimatstok = stok.merk.merk + " " + stok.namaproduk.namaproduk + " " + stok.satuan.satuan + "(" + str(stok.satuan.isi) + ")" + " | EXP:" + kadaluarsa + " | LOT:" + str(lot) + " | Masuk:" + str(stok.tanggal) + "|" + brgpinjam
            res.append((stok.id,kalimatstok))
        return res
    
    # Hitung Jumlah Stok, Dikurangi dengan stok keluar
    def _hitung_jumlah(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for produk in self.browse(cr,uid,ids):
            res[produk.id] = produk.debit - produk.kredit
        return res
    
    # Menghitung nilai produk
    @api.one
    @api.depends("harga","debit")
    def _hitung_bruto(self):
        self.bruto = round(self.harga * self.debit,2)
    
    @api.one
    @api.depends("harga","diskon","debit")
    def _hitung_hpp(self):
        bruto = self.harga * self.debit
        self.hppembelian = round(bruto - bruto * self.diskon / 100,2)
    
    @api.one
    @api.depends("harga","diskon","pajak","debit")
    def _hitung_netto(self):
        bruto = round(self.harga * self.debit,2)
        hpp = round(bruto - bruto * self.diskon / 100,2)    
        self.netto = round(hpp + hpp * self.pajak / 100,2)
    
    # Hitung total barang keluar dari stok keluar    
    def _hitung_kredit(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for stok in self.browse(cr,uid,ids):
            jumlah = 0
            for semuastokkeluar in stok.stokkeluar:
                jumlah += semuastokkeluar.jumlah
            res[stok.id] = jumlah    
        return res        
        
    _columns = {
        'idpembelianpo': fields.many2one("mmr.pembelianpo", "PO Pembelian", related='idpembeliansj.idpo', readonly=True),
        'idpembeliansj': fields.many2one("mmr.pembeliansj", "SJ Pembelian", ondelete='cascade'),
        'idpembelianfaktur': fields.many2one("mmr.pembelianfaktur", "Faktur Pembelian"),
        'idcetakbackup' : fields.many2one("mmr.cetakbackup","cetakbackup"),
        'produk': fields.many2one("mmr.pembelianpodetil", "Produk", required=True, domain="[('idpo', '=', idpembelianpo)]"),
        'tanggal' : fields.date("Tanggal", related='idpembeliansj.tanggalterbit', required=True),
        'gudang': fields.many2one("mmr.gudang","Gudang", related='idpembeliansj.gudang', required=True),
        'merk' : fields.many2one("mmr.merk","Merk", related='produk.merk', readonly=True),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk", related='produk.namaproduk', readonly=True),
        'satuan': fields.many2one("mmr.satuan", "Satuan", related='produk.satuan', readonly=True),
        'harga': fields.float("Harga", related="produk.harga", digits=(12,2)),
        'bruto': fields.float("Bruto", compute="_hitung_bruto", digits=(12,2)),
        'diskon': fields.float("Diskon(%)", related="produk.diskon", digits=(12,2)),
        'hppembelian': fields.float("HP Pembelian", compute="_hitung_hpp", digits=(12,2)),
        'pajak': fields.float("Pajak(%)", related="produk.pajak", digits=(12,2)),
        'netto': fields.float("Netto", compute="_hitung_netto", digits=(12,2)),
        'kadaluarsa': fields.date("Kadaluarsa"),
        'lot': fields.char("LOT"),
        'debit': fields.float("Debit", digits=(12,2)),
        'kredit': fields.function(_hitung_kredit,type="float", method=True,string="Kredit", digits=(12,2)),
        'stokkeluar': fields.one2many("mmr.stokkeluar", "idstok", "Stok Keluar"),
        'saldo': fields.function(_hitung_jumlah, type="float", method=True, string="Saldo", digits=(12,2)),
        'stokkhusus' : fields.boolean("Stok Khusus", related='idpembelianpo.pokhusus', readonly=True),
        'notes' : fields.text("Notes" , related='produk.notes'),
    }    
    
mmr_stok()

class mmr_stokkeluar(osv.osv):
    _name = "mmr.stokkeluar"
    _description = "Modul Stok Keluar untuk PT. MMR."
    
    # Memfilter stok yang dapat dikeluarkan berdasarkan produk yang dipilih
    # Dapat memilih produk apabila diberi ijin otoritas / prosedur khusus
    # Selain itu, stok keluar ditentukan otomatis oleh program
    def onchange_pilihanproduk(self,cr,uid,ids,pilihanproduk,context=None):
        stokClass = self.pool.get("mmr.stok")
        popenjualandetilClass = self.pool.get("mmr.penjualanpodetil")
        popenjualandetilobj = popenjualandetilClass.browse(cr,uid,pilihanproduk)
        hasilsearch = False
        liststok = []
        
        # Cek apakah pelaku memiliki ijin otoritas
        grupClass = self.pool.get("res.groups")
        grupobj = grupClass.search(cr,uid,[('name','=','Otoritas')])
        userClass = self.pool.get("res.users")
        grupditemukan = False
        for semuagrup in userClass.browse(cr,uid,uid).groups_id:
            if semuagrup.id == grupobj[0]:
                grupditemukan = True
        
        if popenjualandetilobj.idpenjualanpo.via == "tukar" or grupditemukan or popenjualandetilobj.idpenjualanpo.bebasexpdate or popenjualandetilobj.idpenjualanpo.tukarbarang:
            if pilihanproduk:
                hasilsearch = stokClass.search(cr,uid,[('namaproduk','=',popenjualandetilobj.namaproduk.id)])
                for semuastok in hasilsearch:
                    stokobj = stokClass.browse(cr,uid,semuastok)
                    saldo = stokobj.debit
                    for semuastokkeluar in stokobj.stokkeluar:
                        saldo -= semuastokkeluar.jumlah
                    if saldo > 0:
                        liststok.append(semuastok)
            return {'domain':{'idstok':[('id','in',liststok)]}}
        else:
            res = {}
            res['idstok'] = False
            res['pilihanproduk'] = False
            return {'value':res}
            
    # Memilih stok yang akan diisi stok keluar, tanpa ijin otoritas tidak dapat mengeluarkan stok secara manual
    def onchange_idstok(self,cr,uid,ids,pilihanproduk,context=None):
        stokClass = self.pool.get("mmr.stok")
        popenjualandetilClass = self.pool.get("mmr.penjualanpodetil")
        popenjualandetilobj = popenjualandetilClass.browse(cr,uid,pilihanproduk)
        hasilsearch = False
        liststok = []
        
        grupClass = self.pool.get("res.groups")
        grupobj = grupClass.search(cr,uid,[('name','=','Otoritas')])
        userClass = self.pool.get("res.users")
        grupditemukan = False
        for semuagrup in userClass.browse(cr,uid,uid).groups_id:
            if semuagrup.id == grupobj[0]:
                grupditemukan = True
                
        if popenjualandetilobj.idpenjualanpo.via == "tukar" or grupditemukan or popenjualandetilobj.idpenjualanpo.bebasexpdate or popenjualandetilobj.idpenjualanpo.tukarbarang:
            if pilihanproduk:
                hasilsearch = stokClass.search(cr,uid,[('namaproduk','=',popenjualandetilobj.namaproduk.id)])
                for semuastok in hasilsearch:
                    stokobj = stokClass.browse(cr,uid,semuastok)
                    saldo = stokobj.debit
                    for semuastokkeluar in stokobj.stokkeluar:
                        saldo -= semuastokkeluar.jumlah
                    if saldo > 0:
                        liststok.append(semuastok)
            return True
        else:
            res = {}
            res['idstok'] = False
            res['pilihanproduk'] = False
            return {'value':res}
        
    @api.one
    @api.depends("idstok")
    def _isi_kelengkapanproduk(self):
        self.gudang = self.idstok.gudang
        self.kadaluarsa = self.idstok.kadaluarsa
        self.lot = self.idstok.lot
    
    @api.one
    @api.depends("harga","jumlah")
    def _hitung_bruto(self):
        self.bruto = round(self.harga * self.jumlah,2)
    
    @api.one
    @api.depends("harga","diskon","jumlah")
    def _hitung_hpp(self):
        bruto = round(self.harga * self.jumlah,2)
        self.hppembelian = round(bruto - bruto * self.diskon / 100,2)
    
    @api.one
    @api.depends("harga","diskon","pajak","jumlah")
    def _hitung_netto(self):
        bruto = round(self.harga * self.jumlah,2)
        hpp = round(bruto - bruto * self.diskon / 100,2)    
        self.netto = round(hpp + hpp * self.pajak / 100,2)        
        
    _columns = {
        'idstok': fields.many2one("mmr.stok","Stok",required=True),
        'pilihanproduk': fields.many2one("mmr.penjualanpodetil", "Produk", required=True, domain="[('idpenjualanpo', '=', idpenjualanpo)]"),
        'idpenjualanpo' : fields.many2one("mmr.penjualanpo", "IDPOPENJUALAN", related="idpenjualansj.idpenjualanpo"),
        'idpenjualanpodetil': fields.many2one("mmr.penjualanpodetil", "IDPOPENJUALANDETIL"),
        'idpenjualansj': fields.many2one("mmr.penjualansj", "IDSJPENJUALAN", ondelete='cascade'),
        'idpenjualanfaktur' : fields.many2one("mmr.penjualanfaktur", "IDFAKTURPENJUALAN"),
        'customer' : fields.many2one("mmr.customer","Customer",related="idpenjualanpo.customer"),
        'teknisi' : fields.boolean("Teknisi (P)"),
        'rayon' : fields.many2one("mmr.rayon","Rayon",related="idpenjualanpo.rayon"),
        'tanggal' : fields.date("Tanggal", related="idpenjualansj.tanggalterbit"),
        'merk' : fields.many2one("mmr.merk","Merk",related="idstok.merk",store=True),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk", related="idstok.namaproduk"),
        'satuan': fields.many2one("mmr.satuan", "Satuan", related="idstok.satuan"),
        'gudang': fields.many2one("mmr.gudang","Gudang", compute="_isi_kelengkapanproduk"),
        'kadaluarsa': fields.date("Kadaluarsa", compute="_isi_kelengkapanproduk"),
        'jumlah': fields.float("Jumlah", required=True, digits=(12,2)),
        'harga': fields.float("Harga", related="pilihanproduk.harga", digits=(12,2)),
        'bruto': fields.float("Bruto", compute="_hitung_bruto", digits=(12,2)),
        'diskon': fields.float("Diskon(%)", related="pilihanproduk.diskon", digits=(12,2)),
        'hppembelian': fields.float("HP Pembelian", compute="_hitung_hpp", digits=(12,2)),
        'pajak': fields.float("Pajak(%)", related="pilihanproduk.pajak", digits=(12,2)),
        'netto': fields.float("Netto", compute="_hitung_netto", digits=(12,2)),
        'lot': fields.char("LOT", compute="_isi_kelengkapanproduk"),
        'notes' : fields.text("Notes"),
    }        
    
mmr_stokkeluar()

class mmr_sisastok(osv.osv):
    
    # Sisa stok akan merangkum stok dan menampilkan stok produk yang masih ada
    # Stok dirangkum berdasarkan expdate, LOT, dan ke-khususan barang
    
    _name = "mmr.sisastok"
    _description = "Modul Sisa Stok untuk PT. MMR. Mengelompokkan stok berdasar gudang, dan exp date"
    
    _columns = {
        'gudang': fields.many2one("mmr.gudang","Gudang", required=True),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk", required=True),
        'kadaluarsa': fields.date("Kadaluarsa", readonly=True),
        'saldo': fields.float("Saldo", readonly=True, digits=(12,2)),
        'warning': fields.boolean("Warning", readonly=True),
        'stokkhusus' : fields.boolean("Stok Khusus", readonly=True),
        'notes' : fields.text("Notes"),
    }        
    
mmr_sisastok()


class mmr_kartustok(osv.osv):
    
    # Rangkuman Stok agar dapat dilihat seperti kartu stok fisik
    # Diurutkan berdasarkan tanggal kejadian
    
    _name = "mmr.kartustok"
    _description = "Modul Kartu Stok untuk PT. MMR. Mengelompokkan stok berdasar gudang, dan exp date"
    
    _columns = {
        'laporanstok': fields.many2one("mmr.laporanstok", "Laporan Stok", ondelete='cascade'),
        'gudang': fields.many2one("mmr.gudang","Gudang"),
        'sumber': fields.char("Sumber"),
        'suppliercustomer' : fields.char("Supplier / Customer"),
        'tanggal': fields.date("Tanggal"),
        'harga': fields.float("Harga", digits=(12,2)),
        'bruto': fields.float("Bruto", digits=(12,2)),
        'diskon': fields.float("Diskon(%)", digits=(12,2)),
        'hppembelian': fields.float("HP Pembelian", digits=(12,2)),
        'hargasetelahdiskon' : fields.float("HPP", digits=(12,2)),
        'kadaluarsa': fields.date("Kadaluarsa"),
        'lot': fields.char("LOT"),
        'debit': fields.float("Debit", digits=(12,2)),
        'kredit' : fields.float("Kredit", digits=(12,2)),
        'saldo' : fields.float("Saldo", digits=(12,2)),
        'nilai' : fields.float("Nilai", digits=(12,2)),
        'stokkhusus' : fields.boolean("Stok Khusus"),
        'notes' : fields.text("Notes"),
    }        
    
mmr_kartustok()

class mmr_laporanstok(osv.osv):
    _name = "mmr.laporanstok"
    _description = "Modul Laporan Stok untuk PT. MMR. Mengelompokkan stok berdasar gudang, dan exp date"
    
    # laporan stok, dimana akan menghitung stok otomatis dan ditampilkan menggunakan kelas kartustok
    # Bedanya dengan stok: Stok masuk memiliki beberapa stok keluar ( unggul ketika kita ingin tahu barang yang keluar berasal dari mana )
    # Kartu stok diurutkan berdasarkan tanggal. Keunggulannya, stok tersusun secara sekuen waktu

    @api.one
    @api.onchange('namaproduk')
    def _isi_kartustok(self):
        if not self.cetak:
            if self.namaproduk:
                # Baca seluruh stok masuk dan keluar
                # Urutkan Berdasarkan waktu
                self.laporanstokdetil = False
                kartustok = {}
                for semuastok in self.namaproduk.stok:
                    kartustok['in'+str(semuastok.id)] = semuastok.idpembeliansj.tanggalterbit
                    for semuastokkeluar in semuastok.stokkeluar:
                        kartustok['ou'+str(semuastokkeluar.id)] = semuastokkeluar.idpenjualansj.tanggalterbit
                
                # Catat jumlah dan nilai secara sekuential juga        
                kartustok = sorted(kartustok.iteritems(), key=lambda (k,v): (v,k))
                jumlah = 0
                nilai = 0
                for semuastok in kartustok:
                    if semuastok[0][0:2] == "in":
                        stokobj = self.env['mmr.stok'].browse(int(semuastok[0][2:]))
                        jumlah += stokobj.debit
                        nilai += round(stokobj.harga * stokobj.debit,2) - round(round(stokobj.harga * stokobj.debit,2) * stokobj.diskon / 100,2)
                        self.laporanstokdetil += self.laporanstokdetil.new({
                                                    'laporanstok' : self.id, 'sumber' : str(stokobj.idpembelianpo.nomorpo), 'suppliercustomer' : stokobj.idpembelianpo.supplier.nama,
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
                        self.laporanstokdetil += self.laporanstokdetil.new({
                                                    'laporanstok' : self.id, 'sumber' : str(stokkeluarobj.idpenjualanpo.nomorpo), 'suppliercustomer' : stokkeluarobj.idpenjualanpo.customer.nama,
                                                    'tanggal' : stokkeluarobj.idpenjualansj.tanggalterbit, 'gudang' : stokkeluarobj.idstok.gudang,
                                                    'harga' : stokkeluarobj.idstok.harga, 'kredit' : stokkeluarobj.jumlah, 'bruto': round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2),
                                                    'diskon':stokkeluarobj.idstok.diskon, 'hppembelian': round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2) - round(round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2) * stokkeluarobj.idstok.diskon / 100,2),
                                                    'kadaluarsa' : stokkeluarobj.idstok.kadaluarsa, 'lot': stokkeluarobj.idstok.lot, 'stokkhusus' : stokkeluarobj.idstok.idpembelianpo.pokhusus,'saldo':jumlah,
                                                    'hargasetelahdiskon' : round((round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2) - round(round(stokkeluarobj.idstok.harga * stokkeluarobj.jumlah,2) * stokkeluarobj.idstok.diskon / 100,2)) / stokkeluarobj.jumlah,2),
                                                    'nilai':nilai
                                                })    
                laporanstokdetilterbalik = self.env['mmr.kartustok']            
                for semuastokdetil in reversed(self.laporanstokdetil):
                    laporanstokdetilterbalik+=semuastokdetil
                self.laporanstokdetil = laporanstokdetilterbalik    
    
    _columns = {
        'idcetakbackup': fields.many2one("mmr.cetakbackup", "ID Cetak Backup"),    
        'merk' : fields.many2one("mmr.merk", "merk"),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk", domain="[('merk', '=', merk)]"),
        'satuan' : fields.many2one("mmr.satuan", "Satuan", related="namaproduk.satuan", readonly=True),
        'laporanstokdetil' : fields.one2many("mmr.kartustok","laporanstok","Kartu Stok", compute="_isi_kartustok"),
        'cetak' : fields.boolean("Cetak"),
    }    
    
    # Tidak perlu menyimpan laporan
    #def create(self,cr,uid,vals,context=None):
        #raise osv.except_osv(_('Tidak Dapat Menyimpan'),_("Laporan ini tidak untuk disimpan!"))
    #    return id    
    
mmr_laporanstok()

# !DEPCRECATED! Gunakan prosedur normal
class mmr_tukarkadaluarsastok(osv.osv):
    _name = "mmr.tukarkadaluarsastok"
    _description = "Modul Tukar Kadaluarsa Stok untuk PT. MMR"
    
    def onchange_idstok(self,cr,uid,ids,idstok,context=None):
        res = {}
        
        res['kadaluarsa'] = self.pool.get("mmr.stok").browse(cr,uid,idstok).kadaluarsa
        
        return {'value':res}
        
    _columns = {
        'idstok': fields.many2one("mmr.stok","Stok", required=True , domain="[('namaproduk', '=', namaproduk)]"),
        'idpembelianpo': fields.many2one("mmr.pembelianpo", "Sumber PO Pembelian", related='idstok.idpembelianpo'),
        'tanggal' : fields.date("Tanggal Masuk", related="idstok.tanggal"),
        'merk' : fields.many2one("mmr.merk","Merk"),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk", domain="[('merk', '=', merk)]"),
        'satuan': fields.many2one("mmr.satuan", "Satuan", related="idstok.satuan"),
        'gudang': fields.many2one("mmr.gudang","Gudang", related="idstok.gudang"),
        'kadaluarsa': fields.date("Kadaluarsa Lama"),
        'lot': fields.char("LOT", related="idstok.lot"),
        'debit': fields.float("Debit", related="idstok.debit", digits=(12,2)),
        'harga': fields.float("Harga", related="idstok.harga", digits=(12,2)),
        'stokkhusus' : fields.boolean("Stok Khusus", related='idstok.stokkhusus'),
        'diskon': fields.float("Diskon(%)", related="idstok.diskon", digits=(12,2)),
        'kadaluarsabaru' : fields.date("Kadaluarsa Baru", required=True),
        'notes' : fields.text("Notes"),
    }
    
    def create(self,cr,uid,vals,context=None):
        id = super(mmr_tukarkadaluarsastok,self).create(cr,uid,vals,context)
        objini = self.browse(cr,uid,id)
        stokClass = self.pool.get("mmr.stok")
        stokClass.write(cr,uid,objini.idstok.id,{'kadaluarsa':objini.kadaluarsabaru})
        return id    
    
    def write(self,cr,uid,ids,vals,context=None):
        raise osv.except_osv(_('Tidak Dapat Mengedit'),_("Perubahan Tanggal Tidak dapat Dianulir / Dihapus!"))
        return True
    
    def unlink(self, cr, uid, ids, context):
        raise osv.except_osv(_('Tidak Dapat Mendelete'),_("Perubahan Tanggal Tidak dapat Dianulir / Dihapus!"))
        return True    
    
mmr_tukarkadaluarsastok()

