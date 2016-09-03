from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools, api
import datetime
import itertools 

class mmr_pembayaranpembelian(osv.osv):
    
    # Pembayaran untuk pembelian yang dilakukan. 
    # Dalam satu pembayaran, dipastikan hanya ke 1 supplier, tetapi dapat dilkaukan untuk beberapa faktur

    _name = "mmr.pembayaranpembelian"
    _description = "Modul Pembayaran Pembelian untuk PT. MMR."
    
    # Pembayaran akan dicocokkan oleh bag. keuangan. Sekali disetujui akan dikunci pembayarannya.
    def setuju(self, cr, uid, ids, context):
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        
        if self.browse(cr,uid,ids).tanggalbayar == False:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Tanggal Bayar Masih Kosong"))    
        self.write(cr,uid,ids,{'disetujui':userobj.login})
                                    
        return { 'type': 'ir.actions.client',
            'tag': 'reload'}
    
    def revisi(self, cr, uid, ids, context):
        self.write(cr,uid,ids,{'disetujui':False})
        
        return { 'type': 'ir.actions.client',
            'tag': 'reload' }
    
    #Hitung total hutang dari seluruh faktur yang dipilih    
    @api.one
    @api.depends("pembayaranpembeliandetil","pembayaranpembeliandetil.hutang","kelebihan","kekurangan","biayatransfer","biayalain")
    def _hitung_hutang(self):
        for semuafaktur in self.pembayaranpembeliandetil:
            self.hutang += semuafaktur.hutang    
            self.bayar += semuafaktur.bayar
            self.bayartotal += semuafaktur.bayar
        self.bayartotal += self.kelebihan    
        self.bayartotal -= self.kekurangan    
        self.bayartotal += self.biayatransfer    
        self.bayartotal += self.biayalain
    
    #Isi jurnal dari template        
    @api.one
    @api.onchange("pembayaranpembeliandetil","aturanakun","akunotomatis","kelebihan","kekurangan","biayatransfer","biayalain")
    def _isi_akun(self):
        if self.bayar!=False and self.aturanakun!=False and self.akunotomatis != False:
            self.akunterkena = False
            data= {'bayar':self.bayar,'hutang':self.hutang, 'kelebihan': self.kelebihan, 'kekurangan': self.kekurangan,
                'biayatransfer' : self.biayatransfer, 'biayalain': self.biayalain, 'bayartotal' : self.bayartotal}
            
            for semuaakundetil in self.aturanakun.aturanakundetil:
                if semuaakundetil.debitkredit =="debit":
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id,"tanggal":self.tanggalbayar, "kredit": 0,
                                                                "debit": data[semuaakundetil.field.name], "sumberpembayaranpembelian": self.id, "notes": False})
                else:
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id,"tanggal":self.tanggalbayar, "debit": 0,
                                                                "kredit": data[semuaakundetil.field.name], "sumberpembayaranpembelian": self.id, "notes": False})
        return self    
    
    # Pembayaran dapat dilakukan dengan beberapa metode, Apabila metode transfer, brt tujuan ke rekening, selain itu ke CP
    def onchange_metode(self,cr,uid,ids,metode,context=None):
        hasil ={}
        if metode!=False:
            if metode == 'transfer':
                hasil['tujuancp'] = False
            else:
                hasil['tujuanrekening'] = False    
        return {'value': hasil}        
    
    # Status pembayaran ( Belum diterima alias belum disetujui, sudah diterima, dan paling akhir, apabila jurnal tidak balance)
    def _set_status(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        res = {}
        for biaya in self.browse(cr,uid,ids):
            res[biaya.id]    = "Belum Diterima"
            
            if biaya.disetujui != False:
                res[biaya.id]    = "Sudah Diterima"
            total = 0    
            for semuaakundetil in biaya.akunterkena:
                total+=semuaakundetil.debit
                total-=semuaakundetil.kredit
            if round(total,2)!=0:
                res[biaya.id]    = "Jurnal Tidak Balance"
        return res
    
            
    _columns = {
            "trigger": fields.char("Trigger",compute="_isi_akun"),
            "supplier" : fields.many2one("mmr.supplier", "Supplier", required=True),
            "tanggalbayar" : fields.date("Tanggal Bayar" , required=True),
            "metode" : fields.selection([('cash','Cash'), ('bg','BG'), ('cek','Cek'), ('transfer','Transfer')], "Metode Pembayaran", required=True),
            "tujuanrekening" : fields.many2one("mmr.nomorrekening", "Rekening Tujuan", domain="[('supplier', '=', supplier)]"),
            "tujuancp": fields.many2one("mmr.cp", "CP Tujuan", domain="[('supplier', '=', supplier)]"),
            "hutang" : fields.float("Total Hutang", compute="_hitung_hutang", digits=(12,2)),
            "bayar": fields.float("Total Pembayaran Sebelum Biaya Tambahan", digits=(12,2), compute="_hitung_hutang", help="Total Pembayaran Sebelum dikenai Biaya Tambahan"),
            'bayartotal' : fields.float("Total Pembayaran Setelah Biaya Tambahan", digits=(12,2), compute="_hitung_hutang", help="Total Pembayaran Setelah dikenai Biaya Tambahan"),
            "pembayaranpembeliandetil": fields.one2many("mmr.pembayaranpembeliandetil","idpembayaranpembelian","List Faktur"),
            'akunotomatis': fields.boolean("Otomatisasi Jurnal", help="Apabila tercentang, jurnal akan diisi otomatis sesuai data yang ada! Sebaliknya, jurnal tidak akan diisi otomatis dan user dapat mengubah jurnal secara manual!"),
            "aturanakun" : fields.many2one("mmr.aturanakun", "Aturan Jurnal", domain="[('model', '=', namamodel)]"),
            "akunterkena" : fields.one2many("mmr.akundetil", "sumberpembayaranpembelian", "Jurnal"),
            'kelebihan': fields.float("Kelebihan", digits=(12,2)),
            'kekurangan': fields.float("Kekurangan, digits=(12,2)"),
            'biayatransfer': fields.float("Biaya Transfer", digits=(12,2)),
            'biayalain': fields.float("Biaya Lain", digits=(12,2)),
            'diedit' : fields.char("Diedit", readonly=True),
            "disetujui" : fields.char("Disetujui", readonly=True),
            "bukti" : fields.binary("Bukti", help="Masukkan Foto Bukti di Sini"),
            "notes" : fields.text("Notes"),
            'namamodel' : fields.char("NamaModel"),
            'status' : fields.function(_set_status,type="char",method=True,string="Status"),
    }    
    
    def create(self,cr,uid,vals,context=None):
        id = super(mmr_pembayaranpembelian,self).create(cr,uid,vals,context)
        objini = self.browse(cr,uid,id)

        validasipembayaranpembelian(self,cr,uid,id)
        return id
    
    def write(self,cr,uid,id,vals,context=None):
        res = super(mmr_pembayaranpembelian,self).write(cr,uid,id,vals,context)
        objini = self.browse(cr,uid,id)
        hasil = {}
        
        # Tandai penyetuju
        if 'supplier' in vals or 'tanggalbayar' in vals or 'metode' in vals or 'tujuanrekening' in vals or 'tujuancp' in vals or 'pembayaranpembeliandetil' in vals or 'akunotomatis' in vals or 'aturanakun' in vals or 'akunterkena' in vals or 'bukti' in vals or 'notes' in vals:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            hasil['diedit'] = userobj.login
            
        res = super(mmr_pembayaranpembelian,self).write(cr,uid,id,hasil,context)    
        validasipembayaranpembelian(self,cr,uid,id)
        return res
    
    # Apabila pembayaran sudah disetujui, jangan dapat dihapus
    def unlink(self, cr, uid, ids, context):
        pembayaranpembeliandetilClass = self.pool.get("mmr.pembayaranpembeliandetil")
        ids=[ids]
        for id in ids:
            pembayaranpembelian = self.browse(cr,uid,id)
            if pembayaranpembelian.disetujui != False and 'ijindelete' not in context:
                raise osv.except_osv(_('Tidak Dapat Menghapus'),_("Pembayaran Telah Disetujui!"))
            for semuapembayaranpembeliandetil in pembayaranpembelian.pembayaranpembeliandetil:
                pembayaranpembeliandetilClass.unlink(cr,uid,semuapembayaranpembeliandetil.id)
            
            super(mmr_pembayaranpembelian, self).unlink(cr, uid, id, context)    
        return True
    
    # Pemabayaran jangan dapat dicopy
    def copy(self, cr, uid, id, default=None, context=None):
           raise osv.except_osv(_('Tidak Dapat Duplikasi'), _('Dilarang melakukan duplikasi data Pembayaran.'))
           return True
       
    _defaults = {
                'namamodel' : "mmr.pembayaranpembelian",
                'akunotomatis' : True,
                }
    
mmr_pembayaranpembelian()

class mmr_pembayaranpembeliandetil(osv.osv):
    _name = "mmr.pembayaranpembeliandetil"
    _description = "Modul Pembayaran Pembelian Detil untuk PT. MMR."
    _rec_name = "idpembayaranpembelian"
    
    # Ambil hutang faktur yang dipilih
    @api.multi
    @api.depends("idfakturpembelian.netto")
    def _get_hutang(self):
        for semuapembayaranpembeliandetil in self:
            semuapembayaranpembeliandetil.hutang = semuapembayaranpembeliandetil.idfakturpembelian.netto

    # Ambil total pembayaran ke faktur ini ( Apabila ada penyicilan, akna terlihat sisa yang harus dibayarkan )        
    @api.multi
    @api.depends("idfakturpembelian")
    def _get_totalbayar(self):
        self.totalbayar = 0
        if self.idfakturpembelian:
            for semuapembayaranpembeliandetil in self.idfakturpembelian.listpembayaran:
                self.totalbayar += semuapembayaranpembeliandetil.bayar

    _columns = {
            "idpembayaranpembelian" : fields.many2one("mmr.pembayaranpembelian", "IDPembayaranpembelian", ondelete='cascade'),
            "supplier" : fields.many2one("mmr.supplier", "Supplier", required=True, related="idpembayaranpembelian.supplier"),
            "idfakturpembelian": fields.many2one("mmr.pembelianfaktur", "Faktur", required=True, domain="[('supplier', '=', supplier),('lunas', '!=', True),('disetujui','!=',False)]"),
            "tanggal" : fields.date("Tanggal Bayar",related="idpembayaranpembelian.tanggalbayar"),
            "hutang" : fields.float("Hutang", compute="_get_hutang", digits=(12,2)),
            'totalbayar' : fields.float("Total Pembayaran", compute="_get_totalbayar", digits=(12,2), help = "Total Pembayaran yang Sudah Dilakukan untuk Faktur Ini"),
            "bayar" : fields.float("Bayar", required=True, digits=(12,2)),
            "notes" : fields.text("Notes"),
    }    
    
    def unlink(self, cr, uid, ids, context=None):
        # Depends tidak akan terpanggil apabila perubahan yang dilakukan adalah pendeletan, sehingga sebelum didelete 
        # perlu write sesuatu agar method depends terpanggil
        self.write(cr,uid,ids,{'bayar':0})
        return super(mmr_pembayaranpembeliandetil, self).unlink(cr, uid, ids, context=context)
    
mmr_pembayaranpembeliandetil()

class mmr_pembayaranpenjualan(osv.osv):
    _name = "mmr.pembayaranpenjualan"
    _description = "Modul Pembayaran Penjualan untuk PT. MMR."
    
    def setuju(self, cr, uid, ids, context):
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        if self.browse(cr,uid,ids).tanggalbayar == False:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Tanggal Bayar Masih Kosong"))    
        
        self.write(cr,uid,ids,{'disetujui':userobj.login})
        return { 'type': 'ir.actions.client',
            'tag': 'reload'}
    
    def revisi(self, cr, uid, ids, context):
        self.write(cr,uid,ids,{'disetujui':False})
        return { 'type': 'ir.actions.client',
            'tag': 'reload' }
        
    @api.one
    @api.depends("pembayaranpenjualandetil","pembayaranpenjualandetil.hutang","kelebihan","kekurangan","biayatransfer","biayalain")
    def _hitung_hutang(self):
        for semuafaktur in self.pembayaranpenjualandetil:
            self.hutang += semuafaktur.hutang    
            self.bayar += semuafaktur.bayar
            self.bayartotal += semuafaktur.bayar
        self.bayartotal += self.kelebihan    
        self.bayartotal -= self.kekurangan    
        self.bayartotal += self.biayatransfer    
        self.bayartotal += self.biayalain
    
    def onchange_metode(self,cr,uid,ids,metode,context=None):
        hasil ={}
        if metode!=False:
            if metode == 'transfer':
                hasil['tujuancp'] = False
            else:
                hasil['tujuanrekening'] = False    
        return {'value': hasil}    
    
    def _set_status(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        res = {}
        for biaya in self.browse(cr,uid,ids):
            res[biaya.id]    = "Belum Diterima"
            if biaya.disetujui != False:
                res[biaya.id]    = "Sudah Diterima"
            total = 0    
            for semuaakundetil in biaya.akunterkena:
                total+=semuaakundetil.debit
                total-=semuaakundetil.kredit
                    
            if round(total,2)!=0:
                res[biaya.id]    = "Jurnal Tidak Balance"
                
        return res
    
    @api.one
    @api.onchange("pembayaranpenjualandetil","aturanakun","akunotomatis","kelebihan","kekurangan","biayatransfer","biayalain")
    def _isi_akun(self):
        if self.bayar!=False and self.aturanakun!=False and self.akunotomatis != False:
            self.akunterkena = False
            data= {'bayar':self.bayar,'hutang':self.hutang, 'kelebihan': self.kelebihan, 'kekurangan': self.kekurangan,
                'biayatransfer' : self.biayatransfer, 'biayalain': self.biayalain, 'bayartotal' : self.bayartotal}
            
            for semuaakundetil in self.aturanakun.aturanakundetil:
                if semuaakundetil.debitkredit =="debit":
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id,"tanggal":self.tanggalbayar, "kredit": 0,
                                                                "debit": data[semuaakundetil.field.name], "sumberpembayaranpenjualan": self.id, "notes": False})
                else:
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id,"tanggal":self.tanggalbayar, "debit": 0,
                                                                "kredit": data[semuaakundetil.field.name], "sumberpembayaranpenjualan": self.id, "notes": False})
        return self    
                
    _columns = {
            "trigger": fields.char("Trigger",compute="_isi_akun"),
            "customer" : fields.many2one("mmr.customer", "Customer", required=True),
            "tanggalbayar" : fields.date("Tanggal Bayar", required=True),
            "metode" : fields.selection([('cash','Cash'), ('bg','BG'), ('cek','Cek'), ('transfer','Transfer')], "Metode Pembayaran", required=True),
            "tujuanrekening" : fields.many2one("mmr.nomorrekening", "Rekening Tujuan", domain="[('customer', '=', customer)]"),
            "tujuancp": fields.many2one("mmr.cp", "CP Tujuan", domain="[('customer', '=', customer)]"),
            "hutang" : fields.float("Total Hutang", compute="_hitung_hutang", digits=(12,2)),
            "bayar": fields.float("Total Pembayaran Sebelum Biaya Tambahan", digits=(12,2), compute="_hitung_hutang", help="Total Pembayaran Sebelum dikenai Biaya Tambahan"),
            'bayartotal' : fields.float("Total Pembayaran Setelah Biaya Tambahan", digits=(12,2), compute="_hitung_hutang", help="Total Pembayaran Setelah dikenai Biaya Tambahan"),
            "pembayaranpenjualandetil": fields.one2many("mmr.pembayaranpenjualandetil","idpembayaranpenjualan","List Faktur"),
            'akunotomatis': fields.boolean("Otomatisasi Jurnal", help="Apabila tercentang, jurnal akan diisi otomatis sesuai data yang ada! Sebaliknya, jurnal tidak akan diisi otomatis dan user dapat mengubah jurnal secara manual!"),
            "aturanakun" : fields.many2one("mmr.aturanakun", "Aturan Jurnal", domain="[('model', '=', namamodel)]"),
            "akunterkena" : fields.one2many("mmr.akundetil", "sumberpembayaranpenjualan", "Jurnal"),
            'kelebihan': fields.float("Kelebihan", digits=(12,2)),
            'kekurangan': fields.float("Kekurangan", digits=(12,2)),
            'biayatransfer': fields.float("Biaya Transfer", digits=(12,2)),
            'biayalain': fields.float("Biaya Lain", digits=(12,2)),
            'diedit' : fields.char("Diedit", readonly=True),
            "disetujui" : fields.char("Disetujui", readonly=True),
            "bukti" : fields.binary("Bukti", help="Masukkan Foto Bukti di Sini"),
            "notes" : fields.text("Notes"),
            'namamodel' : fields.char("NamaModel"),
            'status' : fields.function(_set_status,type="char",method=True,string="Status"),
    }    
    
    _defaults = {
                'namamodel' : "mmr.pembayaranpenjualan",
                'akunotomatis' : True,
                }
    
    def create(self,cr,uid,vals,context=None):
        id = super(mmr_pembayaranpenjualan,self).create(cr,uid,vals,context)
        objini = self.browse(cr,uid,id)

        validasipembayaranpenjualan(self,cr,uid,id)
        return id
    
    def write(self,cr,uid,id,vals,context=None):
        res = super(mmr_pembayaranpenjualan,self).write(cr,uid,id,vals,context)
        objini = self.browse(cr,uid,id)
        hasil = {}
        
        if 'customer' in vals or 'tanggalbayar' in vals or 'metode' in vals or 'tujuanrekening' in vals or 'tujuancp' in vals or 'pembayaranpenjualandetil' in vals or 'akunotomatis' in vals or 'aturanakun' in vals or 'akunterkena' in vals or 'bukti' in vals or 'notes' in vals:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            hasil['diedit'] = userobj.login
            
        res = super(mmr_pembayaranpenjualan,self).write(cr,uid,id,hasil,context)        
        validasipembayaranpenjualan(self,cr,uid,id)
        
        return res
    
    def unlink(self, cr, uid, ids, context):
        pembayaranpenjualandetilClass = self.pool.get("mmr.pembayaranpenjualandetil")
        if type(ids) != "list":
            ids = [ids]
        for id in ids:
            pembayaranpenjualan = self.browse(cr,uid,id)
            if pembayaranpenjualan.disetujui != False and 'ijindelete' not in context:
                raise osv.except_osv(_('Tidak Dapat Menghapus'),_("Pembayaran Telah Disetujui!"))
            for semuapembayaranpenjualandetil in pembayaranpenjualan.pembayaranpenjualandetil:
                pembayaranpenjualandetilClass.unlink(cr,uid,semuapembayaranpenjualandetil.id)
            super(mmr_pembayaranpenjualan, self).unlink(cr, uid, id, context)
            
        return True
    
    def copy(self, cr, uid, id, default=None, context=None):
           raise osv.except_osv(_('Tidak Dapat Duplikasi'), _('Dilarang melakukan duplikasi data Pembayaran.'))
           return True
       
mmr_pembayaranpenjualan()

class mmr_pembayaranpenjualandetil(osv.osv):
    _name = "mmr.pembayaranpenjualandetil"
    _description = "Modul Pembayaran Penjualan Detil untuk PT. MMR."
    _rec_name = "idpembayaranpenjualan"
    
    @api.multi
    @api.depends("idfakturpenjualan.netto")
    def _get_hutang(self):
        for semuapembayaranpenjualandetil in self:
            semuapembayaranpenjualandetil.hutang = semuapembayaranpenjualandetil.idfakturpenjualan.netto
    
    @api.multi
    @api.depends("idfakturpenjualan")
    def _get_totalbayar(self):
        self.totalbayar = 0
        if self.idfakturpenjualan:
            for semuapembayaranpenjualandetil in self.idfakturpenjualan.listpembayaran:
                self.totalbayar += semuapembayaranpenjualandetil.bayar
                    
    _columns = {
            "idpembayaranpenjualan" : fields.many2one("mmr.pembayaranpenjualan", "IDPembayaranpenjualan", ondelete='cascade'),
            "customer" : fields.many2one("mmr.customer", "Customer", required=True, related="idpembayaranpenjualan.customer"),
            "idfakturpenjualan": fields.many2one("mmr.penjualanfaktur", "Faktur", required=True, domain="[('customer', '=', customer),('lunas', '!=', True),('disetujui','!=',False)]"),
            "tanggal" : fields.date("Tanggal Bayar",related="idpembayaranpenjualan.tanggalbayar"),
            "hutang" : fields.float("Hutang", compute="_get_hutang", digits=(12,2)),
            'totalbayar' : fields.float("Total Pembayaran", compute="_get_totalbayar", digits=(12,2), help = "Total Pembayaran yang Sudah Dilakukan untuk Faktur Ini"),
            "bayar" : fields.float("Bayar", required=True, digits=(12,2)),
            "notes" : fields.text("Notes"),
    }    
    
    def unlink(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'bayar':0})
            
        return super(mmr_pembayaranpenjualandetil, self).unlink(cr, uid, ids, context=context)
    
mmr_pembayaranpenjualandetil()

def validasipembayaranpembelian(self,cr,uid,ids):
    pembayaranpembelianClass = self.pool.get("mmr.pembayaranpembelian")
    pembayaranpembeliandetilClass = self.pool.get("mmr.pembayaranpembeliandetil")
    ids = [ids]
    for id in ids:
        # Lihat hutang tiap faktur yang akan dibayarkan, cari seluruh pembayarandetil yang membayar faktur tersebut apabila di +
        # melebihi total hutang, warning
        pembayaranpembelianobj = pembayaranpembelianClass.browse(cr,uid,id)
        for pembayaranpembeliandetil in pembayaranpembelianobj.pembayaranpembeliandetil:
            faktur = pembayaranpembeliandetil.idfakturpembelian
            hasilsearch = pembayaranpembeliandetilClass.search(cr,uid,[("idfakturpembelian","=",faktur.id)])
            totalbayar = 0
            for semuahasilsearch in hasilsearch:
                totalbayar += pembayaranpembeliandetilClass.browse(cr,uid,semuahasilsearch).bayar
            if totalbayar > faktur.netto:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Jumlah dibayar melebihi hutang! (Total hutang: " + str(faktur.netto)
                                                                + ", Total bayar: " + str(totalbayar) + " )"))    
            
def validasipembayaranpenjualan(self,cr,uid,ids):
    pembayaranpenjualanClass = self.pool.get("mmr.pembayaranpenjualan")
    pembayaranpenjualandetilClass = self.pool.get("mmr.pembayaranpenjualandetil")
    ids = [ids]
    for id in ids:
        # Lihat hutang tiap faktur yang akan dibayarkan, cari seluruh pembayarandetil yang membayar faktur tersebut apabila di +
        # melebihi total hutang, warning
        pembayaranpenjualanobj = pembayaranpenjualanClass.browse(cr,uid,id)
        for pembayaranpenjualandetil in pembayaranpenjualanobj.pembayaranpenjualandetil:
            faktur = pembayaranpenjualandetil.idfakturpenjualan
            hasilsearch = pembayaranpenjualandetilClass.search(cr,uid,[("idfakturpenjualan","=",faktur.id)])
            totalbayar = 0
            for semuahasilsearch in hasilsearch:
                totalbayar += pembayaranpenjualandetilClass.browse(cr,uid,semuahasilsearch).bayar
            if totalbayar > faktur.netto:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Jumlah dibayar melebihi hutang! (Total hutang: " + str(faktur.netto)
                                                                + ", Total bayar: " + str(totalbayar) + " )"))            
