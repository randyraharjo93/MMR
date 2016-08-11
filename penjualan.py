from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools,api 
import datetime
import itertools     

# Penjualan secara konsep sama dengan pembelian
# Penjualan lebih fleksibel ( Tidak perlu persetujuan otoritas, dll.) Tetapi lebih rapi dimana, satu Faktur hanya bisa satu SJ
# Memiliki beberapa ijin khusus
class mmr_penjualanpo(osv.osv):
    _name = "mmr.penjualanpo"
    _description = "Modul Penjualan PO untuk PT. MMR."
    _rec_name = "nomorpo"
    
    # Penjualan dapat dibatalkan, tetapi apabila sudah ada SJ / Faktur jangan bisa dibatalkan
    def batal(self,cr,uid,ids,context=None):
        penjualanpoclass = self.pool.get("mmr.penjualanpo")
        penjualanpoobj = penjualanpoclass.browse(cr,uid,ids)
        if len(penjualanpoobj.penjualansj) > 0 or len(penjualanpoobj.penjualanfaktur) > 0:
            raise osv.except_osv(_('Tidak Dapat Dibatalkan'),_("Sudah ada SJ dan Faktur untuk PO ini!"))    
        else:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            penjualanpoclass.write(cr,uid,ids,{'disetujui':userobj.login, 'dibatalkan' : userobj.login})
            
        return True
    
    # Untuk melanjutkan PO Penjualan ( Membuat SJ dan Faktur ) diperlukan minimal persetujuan admin dan  ( sales atau kepala sales )
    def setujuadmin(self, cr, uid, ids, context=None):
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        if self.browse(cr,uid,ids).disetujuisales.id != False or self.browse(cr,uid,ids).disetujuisupervisor.id != False:
            self.write(cr,uid,ids,{'disetujuiadmin':userobj.id,'disetujui':"Ya",'waktudisetujuiadmin':datetime.datetime.today()})
        else:
            self.write(cr,uid,ids,{'disetujuiadmin':userobj.id,'waktudisetujuiadmin':datetime.datetime.today()})    
            
        return True
    
    # Apabila ada ijin khusus ( Kecuali tukar barang ) Perlu disetujui otoritas
    def setujusales(self, cr, uid, ids, context=None):
        userClass = self.pool.get("res.users")
        userobj = userClass.browse(cr,uid,uid)
        objini = self.browse(cr,uid,ids)
        grupClass = self.pool.get("res.groups")
        grupobj = grupClass.search(cr,uid,[('name','=','Admin')])
        grupditemukan = False
        for semuagrup in userClass.browse(cr,uid,uid).groups_id:
            if semuagrup.id == grupobj[0]:
                grupditemukan = True
        if userobj == self.browse(cr,uid,ids).sales.userid or grupditemukan:
            if self.browse(cr,uid,ids).disetujuiadmin.id != False:
                self.write(cr,uid,ids,{'disetujuisales':userobj.id,'disetujui':"Ya",'waktudisetujuisales':datetime.datetime.today()})
            else:
                self.write(cr,uid,ids,{'disetujuisales':userobj.id,'waktudisetujuisales':datetime.datetime.today()})    
        else:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Anda Bukan Sales yang Didaftarkan di PO"))
        
        grupClass = self.pool.get("res.groups")
        grupobj = grupClass.search(cr,uid,[('name','=','Otoritas')])
        grupditemukan = False
        for semuagrup in userClass.browse(cr,uid,uid).groups_id:
            if semuagrup.id == grupobj[0]:
                grupditemukan = True
        if objini.hargabebas and not grupditemukan:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("PO dengan harga bebas butuh Persetujuan Kepala Sales / Otoritas"))
        if objini.tanpafaktur and not grupditemukan:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("PO dengan harga bebas butuh Persetujuan Kepala Sales / Otoritas"))
        
        return True
    
    # Apabila ada ijin khusus ( Kecuali tukar barang ) Perlu disetujui otoritas
    def setujusupervisor(self, cr, uid, ids, context=None):
        userClass = self.pool.get("res.users")
        userobj = userClass.browse(cr,uid,uid)
        
        if self.browse(cr,uid,ids).disetujuiadmin.id != False:
            self.write(cr,uid,ids,{'disetujuisupervisor':userobj.id,'disetujui':"Ya",'waktudisetujuisupervisor':datetime.datetime.today()})
        else:
            self.write(cr,uid,ids,{'disetujuisupervisor':userobj.id,'waktudisetujuisupervisor':datetime.datetime.today()})    
        
        objini = self.browse(cr,uid,ids)
        grupClass = self.pool.get("res.groups")
        grupobj = grupClass.search(cr,uid,[('name','=','Otoritas')])
        grupditemukan = False
        for semuagrup in userClass.browse(cr,uid,uid).groups_id:
            if semuagrup.id == grupobj[0]:
                grupditemukan = True
        if objini.hargabebas and not grupditemukan:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("PO dengan harga bebas butuh Persetujuan Kepala Sales / Otoritas"))
        if objini.tanpafaktur and not grupditemukan:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("PO dengan harga bebas butuh Persetujuan Kepala Sales / Otoritas"))

        return True
    
    # Untuk pertukaran barang, gudang memiliki akses untuk membuat PO Penjualan, tetapi harus menggunakan 'via' tukar
    # Bagian admin juga harus mengetahui, juga harus menggunakan supplier Macrocitra Multicheck
    def setujugudang(self, cr, uid, ids, context=None):
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        if self.browse(cr,uid,ids).tukarbarang != False and self.browse(cr,uid,ids).netto == 0 and self.browse(cr,uid,ids).via == "tukar":
            if self.browse(cr,uid,ids).disetujuiadmin.id != False:
                self.write(cr,uid,ids,{'disetujuisupervisor':userobj.id,'disetujui':"Ya",'waktudisetujuisupervisor':datetime.datetime.today(),
                                    'disetujuisales':userobj.id,'waktudisetujuisales':datetime.datetime.today()})
            else:
                self.write(cr,uid,ids,{'disetujuisupervisor':userobj.id,'waktudisetujuisupervisor':datetime.datetime.today(),
                                    'disetujuisales':userobj.id,'waktudisetujuisales':datetime.datetime.today()})    
        else:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Untuk tukar barang, centang tukar barang, pastikan netto = 0, via melalui tukar"))    
            
        return True
    
    def revisi(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'disetujui':False, 'disetujuiadmin':False,'disetujuisales':False,'disetujuisupervisor':False,
                            'waktudisetujuisupervisor':False, 'waktudisetujuisales': False, 'waktudisetujuiadmin' : False})
        return True
    
    def buatsj(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','mmr_penjualansj')])
        return {
                    'name': 'Surat Jalan Penjualan',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mmr.penjualansj',
                    'context': "{'idpenjualanpo': " +  str(ids[0]) + "}",
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'view_id': self.pool['ir.model.data'].get_object_reference(cr, uid, 'MMR', 'mmr_penjualansj_form')[1],
                    'target': 'new',
                    }
    
    def buatfaktur(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','mmr_penjualanfaktur')])
        return {
                    'name': 'Faktur Penjualan',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mmr.penjualanfaktur',
                    'context': "{'idpenjualanpo': " +  str(ids[0]) + "}",
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'view_id': self.pool['ir.model.data'].get_object_reference(cr, uid, 'MMR', 'mmr_penjualanfaktur_form')[1],
                    'target': 'new',
                    }    
        
    def onchange_customer(self,cr,uid,ids,customer,context=None):
        hasil = {}
        customerClass = self.pool.get("mmr.customer")
        customerobj = customerClass.browse(cr,uid,customer)
        hasil['syaratpembayaran'] = customerobj.syaratpembayaran.id
        
        return {'value': hasil}    
    
    @api.one
    @api.depends("penjualanpodetil")
    def _hitung_harga(self):
        self.bruto, self.diskon, self.hppembelian, self.pajak, self.netto = 0,0,0,0,0
        for semuapodetil in self.penjualanpodetil:
            self.bruto += semuapodetil.bruto
            self.diskon += semuapodetil.bruto - semuapodetil.hppembelian
            self.hppembelian += semuapodetil.hppembelian
            self.pajak += semuapodetil.netto - semuapodetil.hppembelian
            self.netto += semuapodetil.netto
    
    def _set_status(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for penjualanpo in self.browse(cr,uid,ids):
            # Set awal selalu baru
            res[penjualanpo.id] = "Baru"
            lengkap = True
            for penjualanpodetil in penjualanpo.penjualanpodetil:
                if penjualanpodetil.jumlah != penjualanpodetil.jumlahdikirim:
                    lengkap = False
            
            # Cek kelengkapan barang yang dikirim
            if lengkap:
                res[penjualanpo.id] = "Barang Lengkap Dikirim"
            else:
                if penjualanpo.tanggaldijanjikan != False and datetime.datetime.today() > datetime.datetime.strptime(penjualanpo.tanggaldijanjikan,'%Y-%m-%d') :
                    res[penjualanpo.id] = "Barang Terlambat"
            # Apabila penyetuju belum lengkap
            if (penjualanpo.disetujuiadmin.id==False or penjualanpo.disetujuisales.id==False or penjualanpo.disetujuisupervisor.id==False) and penjualanpo.tukarbarang == False:
                res[penjualanpo.id] = "Penyetuju Belum Lengkap"    
            # Apabila PO dibatalkan
            if penjualanpo.dibatalkan != False:
                res[penjualanpo.id] = "Batal"    
                        
        return res
    
    # Milestone PO Penjualan ( Belum ada SJ, Faktur Lengkap, Faktur tidak lengkap, Tanpa Faktur (hanya po khusus) )
    def _set_statusfaktur(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for penjualanpo in self.browse(cr,uid,ids):
            listpenjualansj = []
            # Catat seluruh SJ, Lalu baca seluruh faktur, apabila ada SJ yang tidak ada difaktur, maka set tidak lengkap
            for semuapenjualansj in penjualanpo.penjualansj:
                listpenjualansj.append(semuapenjualansj.id)
            if     len(listpenjualansj) <= 0:
                res[penjualanpo.id] = "Belum ada SJ"
            else:
                for semuapenjualanfaktur in penjualanpo.penjualanfaktur:
                    if semuapenjualanfaktur.penjualansj.id in listpenjualansj:
                        listpenjualansj.remove(semuapenjualanfaktur.penjualansj.id)     
                if len(listpenjualansj) > 0:
                    res[penjualanpo.id] = "Faktur tidak lengkap"
                else:
                    res[penjualanpo.id] = "Faktur lengkap"
            
            # Apabila diberi ijin khusus tanpa faktur / tukar barang
            if penjualanpo.tanpafaktur or penjualanpo.tukarbarang:
                res[penjualanpo.id] = "Tanpa Faktur"    
        return res
    
    # Isi rayon, kota, nomor po berdasarkan customer yang dipilih
    # Penomoran PO dibuat berdasarkan, bulan & tahun
    # PO dengan ijin tanpa faktur dan tukar barang jangan diberi nomor
    def onchange_customer(self,cr,uid,ids,customer,tanggal,sales,tanpafaktur,tukarbarang,context=None):
        hasil = {}
        customerClass = self.pool.get("mmr.customer")
        customerobj = customerClass.browse(cr,uid,customer)
        hasil['syaratpembayaran'] = customerobj.syaratpembayaran.id
        if customer!= False and tanggal!= False and sales!= False:
            customerClass = self.pool.get("mmr.customer")
            customerobj = customerClass.browse(cr,uid,customer)
            salesClass = self.pool.get("mmr.sales")
            salesobj = salesClass.browse(cr,uid,sales)
            sqlQuery = """
            SELECT ID
            FROM mmr_penjualanpo
            WHERE date_part('year', tanggal) = %s AND date_part('month', tanggal) = %s AND tanpafaktur = %s AND tukarbarang = %s
            """% (tanggal[0:4], tanggal[5:7], tanpafaktur, tukarbarang)
            cr.execute(sqlQuery)
            hasilquery = cr.dictfetchall()
            
            nomorterbesar = 0
            for semuahasilquery in hasilquery:
                if self.browse(cr,uid,semuahasilquery['id']).nomorpo != False and self.browse(cr,uid,semuahasilquery['id']).nomorpo[1:5].isdigit():
                    if int(self.browse(cr,uid,semuahasilquery['id']).nomorpo[1:5]) > nomorterbesar:
                        nomorterbesar = int(self.browse(cr,uid,semuahasilquery['id']).nomorpo[1:5])
            nomorpo = nomorterbesar + 1
            if len(ids) == 0:
                if nomorpo < 10:
                    nomorpo = "000" + str(nomorpo)
                elif nomorpo < 100:
                    nomorpo = "00" + str(nomorpo)
                elif nomorpo+1 < 1000:
                    nomorpo = "0" + str(nomorpo)
                else:
                    nomorpo = str(nomorpo)    
                hasil['nomorpo'] = "P" + nomorpo + "/" + "MMR/" + str(salesobj.nama) + "/" + str(customerobj.rayon.kode) + "/" + tanggal[5:7] + "/" + tanggal[0:4]
            else:
                if self.browse(cr,uid,ids).tanggal[0:4] != tanggal[0:4] or self.browse(cr,uid,ids).tanggal[5:7] != tanggal[5:7]  or not tanpafaktur or not tukarbarang:
                    if nomorpo < 10:
                        nomorpo = "000" + str(nomorpo)
                    elif nomorpo < 100:
                        nomorpo = "00" + str(nomorpo)
                    elif nomorpo+1 < 1000:
                        nomorpo = "0" + str(nomorpo)
                    else:
                        nomorpo = str(nomorpo)    
                    hasil['nomorpo'] = "P" + nomorpo + "/" + "MMR/" + str(salesobj.nama) + "/" + str(customerobj.rayon.kode) + "/" + tanggal[5:7] + "/" + tanggal[0:4]
            
            if tanpafaktur or tukarbarang:
                hasil['nomorpo'] = "P - TanpaNomor/" + "MMR/" + str(salesobj.nama) + "/" + str(customerobj.rayon.kode) + "/" + tanggal[5:7] + "/" + tanggal[0:4]
            hasil['rayon'] = customerobj.rayon
            hasil['kota'] = customerobj.kota
        return {'value': hasil}
    
    def onchange_nopo(self,cr,uid,ids,customer,tanggal,sales,tanpafaktur,tukarbarang,context=None):
        hasil = {}
        if customer!= False and tanggal!= False and sales!= False:
            customerClass = self.pool.get("mmr.customer")
            customerobj = customerClass.browse(cr,uid,customer)
            salesClass = self.pool.get("mmr.sales")
            salesobj = salesClass.browse(cr,uid,sales)
            sqlQuery = """
            SELECT ID
            FROM mmr_penjualanpo
            WHERE date_part('year', tanggal) = %s AND date_part('month', tanggal) = %s AND tanpafaktur = %s AND tukarbarang = %s
            """% (tanggal[0:4], tanggal[5:7], tanpafaktur, tukarbarang)
            cr.execute(sqlQuery)
            hasilquery = cr.dictfetchall()
            
            nomorterbesar = 0
            for semuahasilquery in hasilquery:
                if self.browse(cr,uid,semuahasilquery['id']).nomorpo != False and self.browse(cr,uid,semuahasilquery['id']).nomorpo[1:5].isdigit():
                    if int(self.browse(cr,uid,semuahasilquery['id']).nomorpo[1:5]) > nomorterbesar:
                        nomorterbesar = int(self.browse(cr,uid,semuahasilquery['id']).nomorpo[1:5])
            nomorpo = nomorterbesar + 1
            if len(ids) == 0:
                if nomorpo < 10:
                    nomorpo = "000" + str(nomorpo)
                elif nomorpo < 100:
                    nomorpo = "00" + str(nomorpo)
                elif nomorpo+1 < 1000:
                    nomorpo = "0" + str(nomorpo)
                else:
                    nomorpo = str(nomorpo)    
                hasil['nomorpo'] = "P" + nomorpo + "/" + "MMR/" + str(salesobj.nama) + "/" + str(customerobj.rayon.kode) + "/" + tanggal[5:7] + "/" + tanggal[0:4]
            else:
                if self.browse(cr,uid,ids).tanggal[0:4] != tanggal[0:4] or self.browse(cr,uid,ids).tanggal[5:7] != tanggal[5:7] or not tanpafaktur or not tukarbarang:
                    if nomorpo < 10:
                        nomorpo = "000" + str(nomorpo)
                    elif nomorpo < 100:
                        nomorpo = "00" + str(nomorpo)
                    elif nomorpo+1 < 1000:
                        nomorpo = "0" + str(nomorpo)
                    else:
                        nomorpo = str(nomorpo)    
                    hasil['nomorpo'] = "P" + nomorpo + "/" + "MMR/" + str(salesobj.nama) + "/" + str(customerobj.rayon.kode) + "/" + tanggal[5:7] + "/" + tanggal[0:4]
            
            if tanpafaktur or tukarbarang:
                hasil['nomorpo'] = "P - TanpaNomor/" + "MMR/" + str(salesobj.nama) + "/" + str(customerobj.rayon.kode) + "/" + tanggal[5:7] + "/" + tanggal[0:4]
            
            hasil['rayon'] = customerobj.rayon
            hasil['kota'] = customerobj.kota
        return {'value': hasil}
                
    _columns = {
        'nomorpo': fields.char("Nomor PO", required=True, help="Nomor PO Program yang Auto-Generate"),
        'nomorposales' : fields.char("Nomor PO Sales", help="Nomor PO dari Kertas PO yang Dibawa Sales"),
        'nomorpocustomer' : fields.char("Nomor PO Customer", help="Nomor PO dari Customer"),
        'customer' : fields.many2one("mmr.customer", "Customer", required=True),
        'rayon' : fields.many2one("mmr.rayon","Rayon"),
        'kota' : fields.many2one("mmr.kota","Kota"),
        'tanggal' : fields.date("Tanggal Terbit", required=True),
        'status' : fields.function(_set_status,type="char",method=True,string="Status"),
        'statusfaktur' : fields.function(_set_statusfaktur,type="char",method=True,string="Status Faktur"),
        'syaratpembayaran' : fields.many2one("mmr.syaratpembayaran", "Syarat Pembayaran"),
        'tanggaldijanjikan' : fields.date("Tanggal Dijanjikan"),
        "via" : fields.selection([('sms','SMS'), ('telepon','Telepon'), ('sales','Sales'),('langsung','Langsung'),('tukar','Tukar Barang')], "Via", required=True),
        'sales' : fields.many2one("mmr.sales", "Sales", required=True),
        'penjualanpodetil' : fields.one2many("mmr.penjualanpodetil", "idpenjualanpo", "List Produk"),
        'penjualansj' : fields.one2many("mmr.penjualansj", "idpenjualanpo", "List SJ"),
        'penjualanfaktur' : fields.one2many("mmr.penjualanfaktur", "idpenjualanpo", "List Faktur"),
        'bruto': fields.float("Bruto", compute="_hitung_harga", store=True, digits=(12,2)),
        'diskon': fields.float("Diskon", compute="_hitung_harga", store=True, digits=(12,2)),
        'hppembelian': fields.float("HPPenjualan", compute="_hitung_harga", store=True, digits=(12,2)),
        'pajak': fields.float("Pajak", compute="_hitung_harga", store=True, digits=(12,2)),
        'netto': fields.float("Netto", compute="_hitung_harga", store=True, digits=(12,2)),
        'notes' : fields.text("Notes"),
        'dibuat' : fields.char("Dibuat", readonly=True),
        'diedit' : fields.char("Diedit", readonly=True),
        'disetujui' : fields.char("Disetujui", readonly=True),
        'disetujuiadmin' : fields.many2one("res.users","Disetujui Admin", readonly=True),
        'waktudisetujuiadmin' : fields.datetime("Waktu Disetujui Admin", readonly=True),
        'disetujuisales' : fields.many2one("res.users","Disetujui Sales / Gudang", readonly=True, help="Apabila via PO adalah tukar, maka penyetuju adalah gudang"),
        'waktudisetujuisales' : fields.datetime("Waktu Disetujui Sales / Gudang", readonly=True, help="Apabila via PO adalah tukar, maka penyetuju adalah gudang"),
        'disetujuisupervisor' : fields.many2one("res.users","Disetujui Supervisor / Gudang", readonly=True, help="Apabila via PO adalah tukar, maka penyetuju adalah gudang"),
        'waktudisetujuisupervisor' : fields.datetime("Waktu Disetujui Supervisor / Gudang", readonly=True, help="Apabila via PO adalah tukar, maka penyetuju adalah gudang"),
        'dibatalkan' : fields.char("Dibatalkan", readonly=True),
        'laporanmarketing' : fields.many2one("mmr.laporanmarketing","Laporan Marketing"),
        'pokhusus' : fields.boolean("PO Khusus"),
        'hargabebas' : fields.boolean("Harga Bebas"),
        'tanpafaktur' : fields.boolean("Surat Jalan Sementara", help="PO Tidak perlu di faktur, Tidak ada Nomor PO"),
        'bebasexpdate' : fields.boolean("Exp Date Barang Bebas"),
        'tukarbarang' : fields.boolean("Tukar Barang"),
        'popembelian' : fields.many2one("mmr.pembelianpo","Nomor PO Pembelian"),
    }    
    
    _defaults = {
                'tanggal': lambda *a: datetime.datetime.today(),
                'status': "Baru",
                'tanggaldijanjikan': lambda *a: datetime.date.today() + datetime.timedelta(days=7),
                }
    
    # Isi pembuat otomatis
    def create(self,cr,uid,vals,context=None):
        id = super(mmr_penjualanpo,self).create(cr,uid,vals,context)
        hasil = {}
        
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        hasil['dibuat'] = userobj.login
        
        self.write(cr,uid,id,hasil)
        validasipenjualanpo(self,cr,uid,id)
        return id
    
    # Isi pengedit otomatis, jangan lakukan apabila yang dirubah tidak langsung berhubungan dengan PO
    def write(self,cr,uid,ids,vals,context=None):
        res = super(mmr_penjualanpo,self).write(cr,uid,ids,vals,context)
        hasil = {}    
        
        if 'nomorpo' in vals or 'customer' in vals or 'tanggal' in vals or 'tanggaldijanjikan' in vals or 'syaratpembayaran' in vals or 'via' in vals or 'sales' in vals or 'penjualanpodetil' in vals or 'notes' in vals or 'nomorposales' in vals or 'nomorpocustomer' in vals:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            hasil['diedit'] = userobj.login
            
        pobaru = super(mmr_penjualanpo,self).write(cr, uid, ids, hasil, context=context)        
        validasipenjualanpo(self,cr,uid,ids)
        return res
    
    # Jangan dapat dihapus apabila PO telah disetujui admin dan ( sales / kepala sales )
    def unlink(self, cr, uid, ids, context):
        ids = [ids]
        for id in ids:
            penjualanpoobj = self.browse(cr,uid,id)
            if penjualanpoobj.disetujui != False and 'ijindelete' not in context:
                raise osv.except_osv(_('Tidak Dapat Menghapus'),_("PO Penjualan Telah Disetujui!"))
            super(mmr_penjualanpo, self).unlink(cr, uid, id, context)
        return True
    
    # Jangan dapat dicopy
    def copy(self, cr, uid, id, default=None, context=None):
           raise osv.except_osv(_('Tidak Dapat Duplikasi'), _('Dilarang melakukan duplikasi data PO Penjualan.'))
           return True
       
mmr_penjualanpo()

class mmr_penjualanpodetil(osv.osv):
    _name = "mmr.penjualanpodetil"
    _description = "Modul Penjualan PO Detil untuk PT. MMR."

    # Isi informasi jumlah yang telah dikirim berdasarkan SJ Penjualan
    @api.one
    @api.depends("idpenjualanpo.penjualansj")
    def _hitung_jumlahditerima(self):
        jumlah = 0
        for seluruhsjpenjualan in self.idpenjualanpo.penjualansj:
            for seluruhsjpenjualandetil in seluruhsjpenjualan.penjualansjdetil:
                if seluruhsjpenjualandetil.pilihanproduk == self:
                    jumlah+= seluruhsjpenjualandetil.jumlah
        self.jumlahdikirim = jumlah    
    
    # Apabila merk berubah, pilihan produk juga diubah    
    def onchange_merk(self,cr,uid,ids,context=None):
        hasil = {}
        hasil['namaproduk'] = False
        
        return {'value': hasil}
    
    # Hitung kelangkapan harga setelah Sales / Admin mengisi harga
    def onchange_harga(self,cr,uid,ids,jumlah,harga,diskon,pajak,context=None):
        hasil = {}
        hasil['bruto'] = round(jumlah * harga,2)
        hasil['hppembelian'] = round(jumlah * harga - (jumlah * harga * diskon / 100),2)
        hasil['netto'] = round(jumlah * harga - (jumlah * harga * diskon / 100) + (jumlah * harga - (jumlah * harga * diskon / 100)) * pajak / 100,2)

        return {'value': hasil}
    
    # Agar ketika membuat SJ, lebih mudah menentukan barang mana yang datang
    def name_get(self,cr,uid,ids,context):
        res=[]
        for produk in self.browse(cr,uid,ids,context):
            if produk.notes != False:
                kalimatproduk = produk.merk.merk + " " + produk.namaproduk.namaproduk + " ( " + str(produk.jumlah) + " " + produk.satuan.satuan + ", Catatan: " + str(produk.notes) + " )" 
            else:
                kalimatproduk = produk.merk.merk + " " + produk.namaproduk.namaproduk + " ( " + str(produk.jumlah) + " " + produk.satuan.satuan + ", Catatan: " + "-" + " )" 
            res.append((produk.id,kalimatproduk))
            
        return res
    
    # Untuk mempermudah sales / admin menentukan harga jual, munculkan history pembelian suatu barang yang dilakukan customer ini
    @api.one
    @api.onchange("namaproduk")
    def _isi_history(self):
        hasilsearch = self.env['mmr.penjualanpo'].search([("customer","=",self._context.get("default_customer"))])
        listidpenjualanpo = []
        self.stokkeluar = False
        for semuahasilsearch in hasilsearch:
            listidpenjualanpo.append(semuahasilsearch.id)
        hasilsearch = self.env['mmr.stokkeluar'].search([("idpenjualanpo","in",listidpenjualanpo),("namaproduk",'=',self.namaproduk.id)])
        for semuahasilsearch in hasilsearch:
            self.stokkeluar += semuahasilsearch
        self.trigger = "Triggered"
                
    _columns = {
        'waktu': fields.date("Waktu pada PO", related="idpenjualanpo.tanggal", required=True),
        'idpenjualanpo': fields.many2one("mmr.penjualanpo", "idpopenjualan",ondelete='cascade'),
        'merk': fields.many2one("mmr.merk", "Merk", required=True),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk", required=True, domain="[('merk', '=', merk)]"),
        'satuan' : fields.many2one("mmr.satuan", "Satuan", related="namaproduk.satuan", readonly=True),
        'jumlah': fields.integer("Jumlah", required=True),
        'jumlahdikirim' : fields.integer("Jumlah Diterima", compute="_hitung_jumlahditerima"),
        'harga': fields.float("Harga", required=True, digits=(12,2)),
        'bruto': fields.float("Bruto", digits=(12,2)),
        'diskon': fields.float("Diskon(%)", required=True, digits=(12,2)),
        'hppembelian': fields.float("HPPenjualan", digits=(12,2)),
        'pajak': fields.float("Pajak(%)", required=True, digits=(12,2)),
        'netto': fields.float("Netto", digits=(12,2)),
        'stokkeluar' : fields.one2many("mmr.stokkeluar","idpenjualanpodetil","History Harga"),
        'trigger' : fields.char("Trigger", compute="_isi_history"),
        'pengumuman' : fields.char("Pengumuman", related="namaproduk.pengumuman", readonly=True),
        'notes' : fields.text("Notes"),
    }
    
    _defaults = {
                'pajak': 10,
                }    
    
mmr_penjualanpodetil()

class mmr_penjualansj(osv.osv):
    _name = "mmr.penjualansj"
    _description = "Modul SJ Penjualan untuk PT. MMR."
    _rec_name = "nomorsj"
    
    def save(self,cr,uid,ids,context=None):
        return True
    
    # Program akan menentukan barang yang akan dikeluarkan secara otomatis dengan aturan akan mengeluarkan expdate terpendek,
    # apabila ada 2 exp date yang sama, keluarkan dengan metode FIFO
    # Baca setiap SJ detil ( User menentukan ) , cari barang tersebut pada stok, yang kadaluarsanya paling cepat mau habis
    # Ketahui sisa stok, apabila sisa stok > yang diinginkan, buat keluaran stok sesuai yang diinginkan
    # Sebaliknya cari lagi sampai sisa stok > yang diinginkan. Apabila terdapat dua produk sama dalam list sj detil,
    # jangan lupa perhitungkan stok yang sudah digunakan.     
    @api.one
    @api.onchange("penjualansjdetil")
    def _isi_stokkeluar(self):
        self.stokkeluar = False
        stokdipakai = {}
        list_stok_keluar = []
        for semuapenjualansjdetil in self.penjualansjdetil:
            permintaan = semuapenjualansjdetil.jumlah
            while permintaan > 0:
                hasilsearch = self.env['mmr.stok'].search([('namaproduk','=',semuapenjualansjdetil.pilihanproduk.namaproduk.id),('stokkhusus','=',False)])
                kadaluarsa = False
                tglmasuk = False
                sisasaldo = 0
                stokid = False
                uruthasilsearch = {}
                # Agar FIFO urutkan dari tanggal terbit SJ
                for semuastokurut in hasilsearch:
                    uruthasilsearch[semuastokurut] = semuastokurut.idpembeliansj.tanggalterbit
                uruthasilsearch = sorted(uruthasilsearch.iteritems(), key=lambda (k,v): (v,k))    
                hasilsearch = self.env['mmr.stok']
                for semuauruthasilsearch in uruthasilsearch:
                    hasilsearch += semuauruthasilsearch[0]
                for semuastok in hasilsearch:
                    valid = False
                    saldo = semuastok.debit
                    for semuastokkeluar in semuastok.stokkeluar:
                        if semuastokkeluar.idpenjualansj != self:
                            saldo -= semuastokkeluar.jumlah
                    if semuastok in stokdipakai:
                        saldo -= stokdipakai[semuastok]        
                    if saldo > 0:
                        valid = True    
                    if valid and ( semuastok.kadaluarsa <= kadaluarsa or not kadaluarsa ) and (semuastok.tanggal <= tglmasuk or not tglmasuk):
                        tglmasuk = semuastok.tanggal
                        kadaluarsa = semuastok.kadaluarsa
                        sisasaldo = saldo    
                        stokid = semuastok
                        
                if stokid:
                    if sisasaldo >= permintaan:
                        list_stok_keluar.append(self.env['mmr.stokkeluar'].new({'pilihanproduk':semuapenjualansjdetil.pilihanproduk,'idstok':stokid,'jumlah':permintaan,
                                                            'idpenjualanpo':self.idpenjualanpo,'idpenjualansj':self.id}).id)
                        permintaan -= permintaan
                        if stokid in stokdipakai:
                            stokdipakai[stokid] += semuapenjualansjdetil.jumlah
                        else:
                            stokdipakai[stokid] = semuapenjualansjdetil.jumlah 
                    else:
                        list_stok_keluar.append(self.env['mmr.stokkeluar'].new({'pilihanproduk':semuapenjualansjdetil.pilihanproduk,'idstok':stokid,'jumlah':sisasaldo,
                                                            'idpenjualanpo':self.idpenjualanpo,'idpenjualansj':self.id}).id)
                        permintaan -= sisasaldo
                        if stokid in stokdipakai:
                            stokdipakai[stokid] += sisasaldo
                        else:
                            stokdipakai[stokid] = sisasaldo
                else:
                    permintaan = 0
                    self.stokkeluar = False
        self.stokkeluar = [(6, 0, list_stok_keluar)]
    
    # Setujui SJ, akan membuat SJ terkunci dan dapat dicetak admin
    def setuju(self, cr, uid, ids, context=None):
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        
        self.write(cr,uid,ids,{'disetujuigudang':userobj.login})    
        return True
    
    def revisi(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'disetujuigudang':False})    
        return True
                                
    _columns = {
        'idpenjualanpo' :fields.many2one("mmr.penjualanpo", "IDPOPENJUALAN"),    
        'nomorsj': fields.char("Nomor SJ"),
        'tanggalterbit' : fields.date("Tanggal Terbit", required=True),
        'reservednomorsj' : fields.char("Ubah Nomor SJ", help="Apabila kolom ini diisi, nomor SJ akan diubah sesuai dengan kolom ini"),
        'penjualansjdetil' : fields.one2many("mmr.penjualansjdetil", "idpenjualansj", "List Produk"),
        'stokkeluar' : fields.one2many("mmr.stokkeluar", "idpenjualansj", "List Produk"),
        'trigger' : fields.char("Trigger", compute="_isi_stokkeluar"),
        'notes' : fields.text("Notes"),
        'dibuat': fields.char("Dibuat", readonly=True),
        'diedit' : fields.char("Diedit", readonly=True),
        'disetujui' : fields.char("Disetujui", readonly=True),
        'disetujuigudang' : fields.char("Disetujui Gudang", readonly=True),
    }    
    
    _defaults = {
                'idpenjualanpo' : lambda self, cr, uid, c: c.get('idpenjualanpo', False),
                }
    
    def create(self,cr,uid,vals,context=None):
        id = super(mmr_penjualansj,self).create(cr,uid,vals,context)
        hasil = {}
        
        # Isi pembuat
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        hasil['dibuat'] = userobj.login
        
        # Isi Nomor SJ 
        objini = self.browse(cr,uid,id)
        sqlQuery = """
        SELECT ID
        FROM mmr_penjualansj
        WHERE date_part('year', tanggalterbit) = %s AND date_part('month', tanggalterbit) = %s
        """% (objini.tanggalterbit[0:4], objini.tanggalterbit[5:7])
        cr.execute(sqlQuery)
        hasilquery = cr.dictfetchall()
        
        nomorterbesar = 0
        for semuahasilquery in hasilquery:
            if self.browse(cr,uid,semuahasilquery['id']).nomorsj != False and self.browse(cr,uid,semuahasilquery['id']).nomorsj[1:5].isdigit():
                if int(self.browse(cr,uid,semuahasilquery['id']).nomorsj[1:5]) > nomorterbesar:
                    nomorterbesar = int(self.browse(cr,uid,semuahasilquery['id']).nomorsj[1:5])
        hasilnomorsj = nomorterbesar + 1            
        if hasilnomorsj < 10:
            hasilnomorsj = "000" + str(hasilnomorsj)
        elif hasilnomorsj < 100:
            hasilnomorsj = "00" + str(hasilnomorsj)
        elif hasilnomorsj < 1000:
            hasilnomorsj = "0" + str(hasilnomorsj)
        else:
            hasilnomorsj = str(hasilnomorsj)
            
        hasil['nomorsj'] = "S" + hasilnomorsj + "/" + "MMR/" + str(objini.idpenjualanpo.sales.nama) + "/" + str(objini.idpenjualanpo.rayon.kode) + "/" + objini.tanggalterbit[5:7] + "/" + objini.tanggalterbit[0:4]
        if objini.idpenjualanpo.tanpafaktur or objini.idpenjualanpo.tukarbarang:
            hasil['nomorsj'] = "S - " + "Tanpa Nomor/MMR/" + str(objini.idpenjualanpo.sales.nama) + "/" + str(objini.idpenjualanpo.rayon.kode) + "/" + objini.tanggalterbit[5:7] + "/" + objini.tanggalterbit[0:4]

        if objini.reservednomorsj != False:
            hasil['nomorsj'] = objini.reservednomorsj
            
        self.write(cr,uid,id,hasil)    
        validasipenjualansj(self,cr,uid,id)
        return id
    
    def write(self,cr,uid,id,vals,context=None):
        res = super(mmr_penjualansj,self).write(cr,uid,id,vals,context)
        hasil = {}
        
        # Isi pengedit, jangan isi apabila bukan hal yang menyangkut SJ langsung yang diedit
        if 'nomorsj' in vals or 'tanggalterbit' in vals or 'penjualansjdetil' in vals or 'stokkeluar' in vals or 'notes' in vals:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            hasil['diedit'] = userobj.login
        
        objini = self.browse(cr,uid,id)
        if objini.reservednomorsj != False:
            hasil['nomorsj'] = objini.reservednomorsj
            
        res = super(mmr_penjualansj,self).write(cr,uid,id,hasil,context)
        return res
    
    # Jangan bisa didelete apabila sudah disestujui / PO belum disetujui
    def unlink(self, cr, uid, id, context):
        penjualansj = self.browse(cr,uid,id)
        if penjualansj.disetujui != False and 'ijindelete' not in context:
            raise osv.except_osv(_('Tidak Dapat Menghapus'),_("SJ Telah Disetujui!"))
        if penjualansj.idpenjualanpo.disetujui == False and 'ijindelete' not in context:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("PO Belum Disetujui"))    
        return super(mmr_penjualansj, self).unlink(cr, uid, id, context)
    
mmr_penjualansj()    

class mmr_penjualansjdetil(osv.osv):
    _name = "mmr.penjualansjdetil"
    _description = "Modul SJ Penjualan Detil untuk PT. MMR."
        
    _columns = {
        'idpenjualanpo' :fields.many2one("mmr.penjualanpo", "IDPOPENJUALAN", related="idpenjualansj.idpenjualanpo"),    
        'idpenjualansj' :fields.many2one("mmr.penjualansj", "IDSJPENJUALAN", ondelete='cascade'),    
        'pilihanproduk': fields.many2one("mmr.penjualanpodetil", "Produk", required=True, domain="[('idpenjualanpo', '=', idpenjualanpo)]"),
        'merk': fields.many2one("mmr.merk", "Merk", related="pilihanproduk.merk", readonly=True),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk", readonly=True, related="pilihanproduk.namaproduk"),
        'satuan' : fields.many2one("mmr.satuan", "Satuan", related="pilihanproduk.satuan", readonly=True),
        'jumlah' : fields.float("Jumlah", required=True, digits=(12,2)),
        'notes' : fields.text("Notes", related="pilihanproduk.notes"),
    }    
    
mmr_penjualansjdetil()    

class mmr_penjualanfaktur(osv.osv):
    _name = "mmr.penjualanfaktur"
    _description = "Modul Faktur Penjualan untuk PT. MMR."
    _rec_name = "nomorfaktur"
    
    def save(self, cr, uid, ids, context):
        return True
    
    # untuk menyetujui faktur, SJ harus disetujii terlebih dahulu
    def setuju(self, cr, uid, ids, context):
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        self.write(cr,uid,ids,{'disetujui':userobj.login})
                            
        penjualansjClass = self.pool.get("mmr.penjualansj")
        objini = self.browse(cr,uid,ids)
        if objini.penjualansj.nomorsj != False and objini.penjualansj.disetujuigudang != False:
            penjualansjClass.write(cr,uid,objini.penjualansj.id,{'disetujui':userobj.login})        
        else:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Surat Jalan Perlu disetujui dahulu"))    
                                        
        return { 'type': 'ir.actions.client',
            'tag': 'reload'}
    
    def revisi(self, cr, uid, ids, context):
        self.write(cr,uid,ids,{'disetujui':False})
                            
        penjualansjClass = self.pool.get("mmr.penjualansj")
        objini = self.browse(cr,uid,ids)
        if objini.penjualansj.nomorsj != False:
            penjualansjClass.write(cr,uid,objini.penjualansj.id,{'disetujui':False})        
        
        return { 'type': 'ir.actions.client',
            'tag': 'reload' }
    
    # isi jatuh tempo pembayaran otomatis berdasarkan syarat bayar customer
    def onchange_tanggalterbit(self,cr,uid,ids,idpenjualanpo,tanggalterbit,context=None):
        hasil ={}
        if tanggalterbit!=False:
            tanggalterbit = datetime.datetime.strptime(tanggalterbit,"%Y-%m-%d")
            penjualanpoClass = self.pool.get("mmr.penjualanpo")
            penjualanpoobj = penjualanpoClass.browse(cr,uid,idpenjualanpo)
            
            hasil['jatuhtempo'] = tanggalterbit + datetime.timedelta(days = penjualanpoobj.syaratpembayaran.lama)
        return {'value': hasil}    
    
    # Ketika mengisi SJ, tanggal terbit faktur isikan sama ( Hanya secara default, dengan asumsi, SJ dan faktur sangat sering
    # dibuat bersamaan
    def onchange_sj(self,cr,uid,ids,sj,context=None):
        hasil ={}
        penjualansjClass = self.pool.get("mmr.penjualansj")
        penjualansjobj = penjualansjClass.browse(cr,uid,sj)
        
        if sj!=False:
            hasil['tanggalterbit'] = penjualansjobj.tanggalterbit
            
        return {'value': hasil}    
    
    # Hitung harga total barang berdasarkan SJ yang dipilih
    @api.one
    @api.depends("penjualansj.stokkeluar", "biayalain", "idpenjualanpo.penjualanpodetil")
    def _hitung_harga(self):
        bruto, diskon, hpp, pajak, netto = 0,0,0,0,0
        for produk in self.penjualansj.stokkeluar:
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
    
    # Tampilkan barang yang akan dibayar
    # Sebagai informasi akunting
    @api.one
    @api.depends("penjualansj.stokkeluar","idpenjualanpo.penjualanpodetil")    
    def _isi_barang(self):
        self.penjualanfakturdetil = False
        if self.penjualansj.id != False:
            for semuaproduksj in self.penjualansj.stokkeluar:
                self.penjualanfakturdetil += semuaproduksj
    
    # Isi akun dari template
    @api.one
    @api.onchange("penjualansj","aturanakun","akunotomatis","biayalain")
    def _isi_akun(self):
        if self.netto!=False and self.aturanakun!=False and self.akunotomatis != False:
            data= {'bruto':self.bruto,'diskon':self.diskon,'pajak':self.pajak,'biayalain':self.biayalain,'netto':self.netto}
            self.akunterkena = False
            for semuaakundetil in self.aturanakun.aturanakundetil:
                if semuaakundetil.debitkredit =="debit":
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id,"tanggal":self.tanggalterbit, "kredit": 0,
                                                                "debit": data[semuaakundetil.field.name], "sumberpenjualanfaktur": self.id, "notes": False})
                else:
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id,"tanggal":self.tanggalterbit, "kredit": 0,
                                                                "kredit": data[semuaakundetil.field.name], "sumberpenjualanfaktur": self.id, "notes": False})
        return self
    
    def _set_status(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        res = {}
        grupClass = self.pool.get("res.groups")
        grupobj = grupClass.search(cr,uid,[('name','=','Akunting')])
        userClass = self.pool.get("res.users")
        grupditemukan = False
        for semuagrup in userClass.browse(cr,uid,uid).groups_id:
            if semuagrup.id == grupobj[0]:
                grupditemukan = True
        
        pembayaranpenjualandetilClass = self.pool.get("mmr.pembayaranpenjualandetil")
        if grupditemukan:
            for penjualanfaktur in self.browse(cr,uid,ids):
                # 1. Selalu set belum lunas
                res[penjualanfaktur.id]    = "Belum Lunas"
                
                # 2. Cek pembayaran, antara cicil --> ada peembayaran tp tidak membuat lunas, lunas --> Sudah tidak hutang    
                hasilsearch = pembayaranpenjualandetilClass.search(cr,uid,[("idfakturpenjualan","=",penjualanfaktur.id)])
                total = 0
                for semuahasilsearch in hasilsearch:
                    pembayaranpenjualandetilobj = pembayaranpenjualandetilClass.browse(cr,uid,semuahasilsearch)
                    total += pembayaranpenjualandetilobj.bayar
                if total > 0 and total < penjualanfaktur.netto:
                    res[penjualanfaktur.id]    = "Cicil"
                elif total == penjualanfaktur.netto:
                    res[penjualanfaktur.id] = "Lunas"
                if     penjualanfaktur.setlunas:
                    res[penjualanfaktur.id] = "Lunas"
                
                # 3. Warning --> pembayaran belum beres walau sudah lewat jatuh tempo
                if datetime.datetime.today() > datetime.datetime.strptime(penjualanfaktur.jatuhtempo,'%Y-%m-%d') and res[penjualanfaktur.id] != "Lunas":
                    res[penjualanfaktur.id] = "Warning"
                
                # 4. Jurnal tidak balance --> Kalau jurnal tidak imbang debit kreditnya    
                total = 0
                for semuaakundetil in penjualanfaktur.akunterkena:
                    total+=semuaakundetil.debit
                    total-=semuaakundetil.kredit
                        
                if round(total,2)!=0:
                    res[penjualanfaktur.id]    = "Jurnal Tidak Balance"
        return res
    
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
    
    # Nomor faktur pasti sama dengan nomor SJ, hanya S diganti F
    @api.one
    @api.depends("penjualansj","penjualansj.nomorsj")
    def _set_nomor_faktur(self):
        if self.penjualansj:
            self.nomorfaktur = "F" + self.penjualansj.nomorsj[1:]
    
    # Informasikan ke user total pembayaran faktur ini
    def _isi_totalbayar(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        res = {}
        for penjualanfaktur in self.browse(cr,uid,ids):
            res[penjualanfaktur.id] = 0
            for semuapembayaran in penjualanfaktur.listpembayaran:
                res[penjualanfaktur.id] += semuapembayaran.bayar    
            if penjualanfaktur.lunas:
                res[penjualanfaktur.id] = penjualanfaktur.netto    
        return res
    
    # Untuk mengatasi barang sama dicetak 2 baris ( Disebabkan barang exp date sama, tetapi tanggal masuk berbeda ) 
    # Kumpulkan seluruh barang yang sama ( Termasuk exp dan lot ) menjadi satu
    @api.one
    @api.depends("penjualansj.stokkeluar","idpenjualanpo.penjualanpodetil")    
    def _isi_cetak_faktur(self):
        self.cetakfaktur = False
        if self.penjualansj.id != False:
            listproduk = {}
            for semuaproduksj in self.penjualansj.stokkeluar:
                if str(semuaproduksj.merk.id) + "/" + str(semuaproduksj.satuan.id) + "/"  + str(semuaproduksj.namaproduk.id) + "/" + str(semuaproduksj.harga) + "/" + str(semuaproduksj.diskon) + "/" + str(semuaproduksj.pajak) + "/" + str(semuaproduksj.kadaluarsa) + "/"  + str(semuaproduksj.lot) + "/"  + str(semuaproduksj.teknisi) in listproduk:
                    listproduk[str(semuaproduksj.merk.id) + "/" + str(semuaproduksj.satuan.id) + "/"  + str(semuaproduksj.namaproduk.id) + "/" + str(semuaproduksj.harga) + "/" + str(semuaproduksj.diskon) + "/" + str(semuaproduksj.pajak) + "/" + str(semuaproduksj.kadaluarsa) + "/"  + str(semuaproduksj.lot) + "/"  + str(semuaproduksj.teknisi)] += semuaproduksj.jumlah
                else:
                    listproduk[str(semuaproduksj.merk.id) + "/"  + str(semuaproduksj.satuan.id) + "/" + str(semuaproduksj.namaproduk.id) + "/" + str(semuaproduksj.harga) + "/" + str(semuaproduksj.diskon) + "/" + str(semuaproduksj.pajak) + "/" + str(semuaproduksj.kadaluarsa) + "/"  + str(semuaproduksj.lot) + "/"  + str(semuaproduksj.teknisi)] = semuaproduksj.jumlah
            
            for semuaproduk in listproduk:
                produk = semuaproduk.split("/")
                nilaihpp = round(float(produk[3]) * listproduk[semuaproduk],2) - round(round(round(float(produk[3]) * listproduk[semuaproduk],2) * float(produk[4]),2) / 100,2)
                teknisi = False
                if produk[8] == "True":    
                    teknisi = True
                self.cetakfaktur += self.env['mmr.cetakfaktur'].new({'idpenjualanfaktur':self.id, 
                                                                    'merk': int(produk[0]),
                                                                    'teknisi': teknisi,
                                                                    'namaproduk' : int(produk[2]),
                                                                    'satuan' : int(produk[1]),
                                                                    'jumlah' : listproduk[semuaproduk],
                                                                    'harga' : round(float(produk[3]), 2),
                                                                    'diskon' : round(float(produk[4]), 2),
                                                                    'hppembelian' : nilaihpp})

    _columns = {
        'idpenjualanpo' :fields.many2one("mmr.penjualanpo", "IDPOPENJUALAN"),    
        'customer' : fields.many2one("mmr.customer", "Customer", related="idpenjualanpo.customer",required=True),
        'rayon' : fields.many2one("mmr.rayon","Rayon",related="idpenjualanpo.rayon"),
        'kota' : fields.many2one("mmr.kota","Kota",related="idpenjualanpo.kota"),
        'teknisi' : fields.boolean("Teknisi(P)",help="Centang apabila alat dirawat Teknisi."),
        'nomorfaktur': fields.char("Nomor Faktur", compute=_set_nomor_faktur),
        'nofakturpajak': fields.char("Nomor Faktur Pajak"),
        'waktu' : fields.datetime("Waktu",required=True),
        'status' : fields.function(_set_status,type="char",method=True,string="Status"),
        'lunas' : fields.boolean("Lunas",compute="_set_lunas"),
        'setlunas' : fields.boolean("Lunas",help="Apabila penjualan dilakukan secara tunai, dan faktur langsung lunas, centang tombol ini!"),
        'jatuhtempo': fields.date("Jatuh Tempo",required=True),
        'tanggalterbit' : fields.date("Tanggal Terbit", required=True),
        'penjualansj' : fields.many2one("mmr.penjualansj", "Surat Jalan", domain="[('idpenjualanpo', '=', idpenjualanpo)]", required=True),
        'penjualanfakturdetil' : fields.one2many("mmr.stokkeluar", "idpenjualanfaktur", "ListBarang",compute="_isi_barang"),
        'cetakfaktur' : fields.one2many("mmr.cetakfaktur","idpenjualanfaktur","Tabel Cetak", compute="_isi_cetak_faktur"),
        'aturanakun' : fields.many2one("mmr.aturanakun", "Aturan Jurnal", required=True, domain="[('model', '=', namamodel)]"),
        'akunterkena' : fields.one2many("mmr.akundetil","sumberpenjualanfaktur","Akuntansi"),
        'listpembayaran' : fields.one2many("mmr.pembayaranpenjualandetil","idfakturpenjualan","List Penjualan"),
        'totalbayar' : fields.function(_isi_totalbayar,type="float",method=True,string="Total Pembayaran", digits=(12,2)),
        'trigger' : fields.char("Trigger",compute="_isi_akun"),
        'bruto' : fields.float("Bruto", compute="_hitung_harga", digits=(12,2)),
        'diskon' : fields.float("Diskon", compute="_hitung_harga", digits=(12,2)),
        'hppembelian' : fields.float("HPPenjualan", compute="_hitung_harga", digits=(12,2)),
        'pajak' : fields.float("Pajak", compute="_hitung_harga", digits=(12,2)),
        'biayalain' : fields.float("Biaya Lain", digits=(12,2)),
        'netto' : fields.float("Netto", compute="_hitung_harga", digits=(12,2)),
        'notes' : fields.text("Notes"),
        'dibuat': fields.char("Dibuat", readonly=True),
        'diedit': fields.char("Diedit", readonly=True),
        'disetujui' : fields.char("Disetujui", readonly=True),
        'akunotomatis': fields.boolean("Otomatisasi Jurnal", help="Apabila tercentang, jurnal akan diisi otomatis sesuai data yang ada! Sebaliknya, jurnal tidak akan diisi otomatis dan user dapat mengubah jurnal secara manual!"),
        'namamodel' : fields.char("NamaModel"),
        'notes' : fields.text("Notes"),
        'laporanmarketing' : fields.many2one("mmr.laporanmarketing","Laporan Marketing"),
    }    
    
    _defaults = {
                'idpenjualanpo' : lambda self, cr, uid, c: c.get('idpenjualanpo', False),
                'waktu': lambda *a: datetime.datetime.today(),
                'akunotomatis': True,
                'status': "Belum Lunas",
                'namamodel' : "mmr.penjualanfaktur",
                'lunas' : False
                }
    
    def create(self,cr,uid,vals,context=None):
        id = super(mmr_penjualanfaktur,self).create(cr,uid,vals,context)
        hasil = {}
        
        # Isi Pembuat
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        hasil['dibuat'] = userobj.login
        
        self.write(cr,uid,id,hasil)    
        validasipenjualanfaktur(self,cr,uid,id)
        return id
    
    def write(self,cr,uid,id,vals,context=None):
        res = super(mmr_penjualanfaktur,self).write(cr,uid,id,vals,context)
        hasil = {}
        
        # Isi Pengedit
        if 'customer' in vals or 'nomorfaktur' in vals or 'waktu' in vals or 'jatuhtempo' in vals or 'tanggalterbit' in vals or 'penjualansj' in vals or 'aturanakun' in vals or 'akunterkena' in vals or 'biayalain' in vals or 'akunotomatis' in vals or 'notes' in vals:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr,uid,uid)
            hasil['diedit'] = userobj.login
            
        res = super(mmr_penjualanfaktur,self).write(cr,uid,id,hasil,context)
        validasipenjualanfaktur(self,cr,uid,id)
        return res
    
    # Jangan bisa dihapus apabila faktur telah disetujui
    def unlink(self, cr, uid, id, context):
        penjualanfaktur = self.browse(cr,uid,id)
        if penjualanfaktur.disetujui != False and 'ijindelete' not in context:
            raise osv.except_osv(_('Tidak Dapat Menghapus'),_("Faktur Telah Disetujui!"))
        if penjualanfaktur.idpenjualanpo.disetujui == False and 'ijindelete' not in context:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("PO Belum Disetujui"))    
        
        return super(mmr_penjualanfaktur, self).unlink(cr, uid, id, context)
    
mmr_penjualanfaktur()    

class mmr_cetakfaktur(osv.osv):
    _name = "mmr.cetakfaktur"
    _description = "Modul Tabel Faktur yang Dicetak untuk PT. MMR."
    
    _columns = {
        'idpenjualanfaktur' :fields.many2one("mmr.penjualanfaktur","IDPOPENJUALANFAKTUR", ondelete='cascade'),
        'idcetakbackup' :fields.many2one("mmr.cetakbackup","IDCETAKBACKUP"),
        'teknisi' : fields.boolean("Teknisi(P)"),
        'merk': fields.many2one("mmr.merk", "Merk"),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk"),
        'satuan' : fields.many2one("mmr.satuan", "Satuan"),
        'jumlah' : fields.float("Jumlah", digits=(12,2)),
        'harga': fields.float("Harga", digits=(12,2)),
        'diskon': fields.float("Diskon(%)", digits=(12,2)),
        'hppembelian': fields.float("HPPenjualan", digits=(12,2)),
        'notes': fields.text("Notes"),
    }    
    
mmr_cetakfaktur()

# Sebisa mungkin, retur tidak dilakukan, sampai terjadi retur, gunakan pembelian untuk menerima barang kembali dari customer
# Buat Jurnalnya menggunakan kegiatan akunting, cukup pastikan sudah dijurnal, lalu check pada form ini
# Hubungkan dengan penjualan yang diretur, agar nilai penjualan rayon / sales dapat dikurangi
class mmr_penjualanretur(osv.osv):
    _name = "mmr.penjualanretur"
    _description = "Modul Penjualan Retur untuk PT. MMR."
    
    def setuju(self, cr, uid, ids, context):
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr,uid,uid)
        self.write(cr,uid,ids,{'disetujui':userobj.login})
                            
        return { 'type': 'ir.actions.client',
            'tag': 'reload'}
    
    def revisi(self, cr, uid, ids, context):
        
        self.write(cr,uid,ids,{'disetujui':False})
        return { 'type': 'ir.actions.client',
            'tag': 'reload' }
            
    @api.one
    @api.onchange("idpembeliansj")    
    def _isi_barang(self):
        # Pembelianfaktur detil sama saja dengan stok, oleh sebab itu stok diberi kelangkapan harga,
        # Pada faktur tinggal menggunakan ini untuk mengisi one2manynya, tidak pakai related karena akan kacau
        self.penjualanreturdetil = False
        #pembeliansjobj = pembeliansjClass.browse(self._cr,self._uid,semuasj.id,self._context)
        for semuaproduksj in self.idpembeliansj.pembeliansjdetil:
            self.penjualanreturdetil += self.env['mmr.penjualanreturdetil'].new({'idpenjualanretur':self.id,'merk':semuaproduksj.merk,
                                                                    'namaproduk':semuaproduksj.namaproduk,'satuan':semuaproduksj.satuan
                                                                    ,'jumlah':semuaproduksj.debit, 'harga':0,'diskon':0,'pajak':10})
        self.trigger="Triggered"    
    
    @api.one
    @api.depends("penjualanreturdetil")
    def _hitung_harga(self):
        self.bruto, self.diskon, self.hppembelian, self.pajak, self.netto = 0,0,0,0,0
        for semuareturdetil in self.penjualanreturdetil:
            self.bruto += semuareturdetil.bruto
            self.diskon += semuareturdetil.bruto - semuareturdetil.hppembelian
            self.hppembelian += semuareturdetil.hppembelian
            self.pajak += semuareturdetil.netto - semuareturdetil.hppembelian
            self.netto += semuareturdetil.netto
    
    def _set_lunas(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for penjualanretur in self.browse(cr,uid,ids):
            res[penjualanretur.id] = False
            if penjualanretur.netto == penjualanretur.dibayar:
                res[penjualanretur.id] = True
                
        return res        
    
    def _set_status(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for penjualanretur in self.browse(cr,uid,ids):
            res[penjualanretur.id] = "Lunas"
            if not penjualanretur.jurnalretur or not penjualanretur.jurnalpembayaranretur:
                res[penjualanretur.id] = "Jurnal Belum Beres"
            if not penjualanretur.lunas:
                res[penjualanretur.id] = "Belum Lunas"    
                
        return res    
                    
    _columns = {
        'nomorretur' :fields.char("Nomor Retur"),    
        'idpopenjualan' : fields.many2one("mmr.penjualanpo","Nomor PO Penjualan", required=True, help="Pilih PO Penjualan yang akan diretur"),
        'idpopembelian' : fields.many2one("mmr.pembelianpo", "Nomor PO Pembelian Retur",  required=True, help="Pilih PO Pembelian Retur yang Bersangkutan", domain="[('supplier','=','RTR')]"),
        'idpembeliansj' :fields.many2one("mmr.pembeliansj","Nomor SJ Pembelian Retur",  required=True, help="Pilih SJ Pembelian Retur yang Bersangkutan", domain="[('idpo','=',idpopembelian)]"),
        'tanggalterbit' : fields.date("Tanggal Terbit", required=True),
        'bruto': fields.float("Bruto", digits=(12,2), compute="_hitung_harga"),
        'diskon': fields.float("Diskon(%)", digits=(12,2), compute="_hitung_harga"),
        'hppembelian': fields.float("HPPenjualan", digits=(12,2), compute="_hitung_harga"),
        'pajak': fields.float("Pajak(%)", digits=(12,2), compute="_hitung_harga"),
        'netto': fields.float("Netto", digits=(12,2), compute="_hitung_harga"),
        'nomorfakturretur' : fields.char("Nomor Faktur Retur"),
        'nomorfakturreturpajak' : fields.char("Nomor Pajak Faktur Retur"),
        'penjualanreturdetil' : fields.one2many("mmr.penjualanreturdetil","idpenjualanretur","List produk", store=True),
        'dibayar' : fields.float("Dibayar", digits=(12,2)),
        'jurnalretur' : fields.boolean("Jurnal Faktur Retur", help="Centang apabila anda telah menjurnalkan faktur retur di kegiatan akunting"),
        'jurnalpembayaranretur' : fields.boolean("Jurnal Pembayaran Retur", help="Centang apabila anda telah menjurnalkan pembayaran retur di kegiatan akunting"),
        'lunas' : fields.function(_set_lunas,type="boolean",method=True,string="Lunas"),
        'notes' : fields.text("Notes"),
        'disetujui' : fields.char("Disetujui", readonly=True),
        'trigger' : fields.char("Trigger", compute="_isi_barang"),
        'status' : fields.function(_set_status,type="char",method=True,string="Status"),
        'laporanmarketing' : fields.many2one("mmr.laporanmarketing","Laporan Marketing"),
        'teknisi' : fields.boolean("Teknisi(P)", help="Centang apabila retur ini mempengaruhi omzet teknisi"),

    }
    
    def unlink(self, cr, uid, id, context=None):
        penjualanretur = self.browse(cr,uid,id)
        if penjualanretur.disetujui != False:
            raise osv.except_osv(_('Tidak Dapat Menghapus'),_("Retur Telah Disetujui!"))
        
        return super(mmr_penjualanretur, self).unlink(cr, uid, id, context=context)
    
    _defaults = {
                'lunas' : False
                }    
    
mmr_penjualanretur()    

class mmr_penjualanreturdetil(osv.osv):
    _name = "mmr.penjualanreturdetil"
    _description = "Modul Penjualan Retur Detil untuk PT. MMR."
    
    def onchange_harga(self,cr,uid,ids,jumlah,harga,diskon,pajak,context=None):
        hasil = {}
        hasil['bruto'] = round(jumlah * harga,2)
        hasil['hppembelian'] = round(jumlah * harga - (jumlah * harga * diskon / 100),2)
        hasil['netto'] = round(jumlah * harga - (jumlah * harga * diskon / 100) + (jumlah * harga - (jumlah * harga * diskon / 100)) * pajak / 100,2)

        return {'value': hasil}
        
    _columns = {
        'idpenjualanretur' :fields.many2one("mmr.penjualanretur","IDPOPENJUALANRETUR",ondelete='cascade'),
        'merk': fields.many2one("mmr.merk", "Merk"),
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk"),
        'satuan' : fields.many2one("mmr.satuan", "Satuan"),
        'jumlah' : fields.float("Jumlah", digits=(12,2)),
        'harga': fields.float("Harga", required=True, digits=(12,2)),
        'bruto': fields.float("Bruto", digits=(12,2)),
        'diskon': fields.float("Diskon(%)", required=True, digits=(12,2)),
        'hppembelian': fields.float("HPPenjualan", digits=(12,2)),
        'pajak': fields.float("Pajak(%)", required=True, digits=(12,2)),
        'netto': fields.float("Netto", digits=(12,2)),
        'notes': fields.text("Notes"),
    }    
    
    _defaults = {
                'pajak':10
                }    
mmr_penjualanreturdetil()    

def validasipenjualanpo(self,cr,uid,id,context=None):

    # Cek Harga agar tidak dibawah minimum jual, kecuali jika dibuat otoritas
    thisObj = self.browse(cr,uid,id)
    
    grupClass = self.pool.get("res.groups")
    grupobj = grupClass.search(cr,uid,[('name','=','Otoritas')])
    userClass = self.pool.get("res.users")
    grupditemukan = False
    for semuagrup in userClass.browse(cr,uid,uid).groups_id:
        if semuagrup.id == grupobj[0]:
            grupditemukan = True
    
    grupobj = grupClass.search(cr,uid,[('name','=','Kepala Sales')])
    kepalasalesditemukan = False
    for semuagrup in userClass.browse(cr,uid,thisObj.sales.userid.id).groups_id:
        if semuagrup.id == grupobj[0]:
            kepalasalesditemukan = True
    
    # Jika parent minimal jual > harga jual ini, warning
    for semuaproduk in thisObj.penjualanpodetil:
        if kepalasalesditemukan:
            if semuaproduk.jumlah !=0 and semuaproduk.hppembelian / semuaproduk.jumlah < round(semuaproduk.namaproduk.hargajualterendah - round(semuaproduk.namaproduk.hargajualterendah*10/100,2),2) and not grupditemukan and thisObj.hargabebas == False and thisObj.tukarbarang == False:
                raise osv.except_osv(_('Tidak Dapat Membuat'),_("Harga Jual Dibawah Harga Jual Minimum - 10% (Khusus Supervisor Sales)!"))
        else:
            if semuaproduk.jumlah !=0 and semuaproduk.hppembelian / semuaproduk.jumlah < semuaproduk.namaproduk.hargajualterendah and not grupditemukan and thisObj.hargabebas == False and thisObj.tukarbarang == False:
                raise osv.except_osv(_('Tidak Dapat Membuat'),_("Harga Jual Dibawah Harga Jual Minimum!"))
        
    # CEK JUMLAH BARANG TIDAK BERKURANG LEBIH DARI YANG SUDAH DIKIRIM
    listbarang = {}
    for semuaprodukpenjualandetil in thisObj.penjualanpodetil:
        if semuaprodukpenjualandetil not in listbarang:
            listbarang[semuaprodukpenjualandetil] = semuaprodukpenjualandetil.jumlah
        else:
            listbarang[semuaprodukpenjualandetil] += semuaprodukpenjualandetil.jumlah
            
    for semuapenjualansj in thisObj.penjualansj:
        for semuapenjualansjdetil in semuapenjualansj.penjualansjdetil:
            if    semuapenjualansjdetil.pilihanproduk not in listbarang:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Barang yang Dikirim Tidak Sesuai yang Dipesan!"))
            else:
                listbarang[semuapenjualansjdetil.pilihanproduk] -= semuapenjualansjdetil.jumlah
                    
    for semualistbarang in listbarang:
        if listbarang[semualistbarang] < 0:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Barang yang Dikirim Lebih Banyak dari yang Dipesan! (" + str(semualistbarang.namaproduk.namaproduk) + " Lebih: " + str(listbarang[semualistbarang]*-1)+")"))    
    
    # Pastikan total PO tidak akan melebihi batas hutang ke supplier ini.
    customerClass = self.pool.get("mmr.customer")
    pembayaranpenjualanClass = self.pool.get("mmr.pembayaranpenjualan")
    customerobj = customerClass.browse(cr,uid,thisObj.customer.id)
    # Hitung Total Hutang, Cari Seluruh PO dengan supplier ini
    # Ambil seluruh fakturnya, jumlahkan nettonya
    # Ambil seluruh pembayaran dari supplier ini, kurangkan jumlah dengan bayar
    total = 0
    for semuapo in self.browse(cr,uid,self.search(cr,uid,[('customer','=',thisObj.customer.id)])):
        for semuafaktur in semuapo.penjualanfaktur:
            total+=semuafaktur.netto
    for semuapembayaran in pembayaranpenjualanClass.browse(cr,uid,pembayaranpenjualanClass.search(cr,uid,[('customer','=',thisObj.customer.id)])):
        total-=semuapembayaran.bayar
    
    if total > customerobj.batashutang:
        raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Melebihi Batas Piutang Kepada Customer!"))
    
    # Pastikan apabila menukar barang, barang yang ditukar sama, dan jumlahnya sama
    if thisObj.tukarbarang:
        if thisObj.popembelian.supplier.nama == "Macrocitra Multicheck":
            barangpobeli = {}
            for semuabarangpobeli in thisObj.popembelian.pembelianpodetil:
                if semuabarangpobeli.namaproduk not in barangpobeli:
                    barangpobeli[semuabarangpobeli.namaproduk] = semuabarangpobeli.jumlah
                else:
                    barangpobeli[semuabarangpobeli.namaproduk] += semuabarangpobeli.jumlah
            for semuabarangpojual in thisObj.penjualanpodetil:
                if semuabarangpojual.namaproduk not in barangpobeli:
                    raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Salah barang yang ditukar!"))
                else:
                    barangpobeli[semuabarangpojual.namaproduk] -= semuabarangpojual.jumlah
            for semuabarangpobeli in barangpobeli:
                if barangpobeli[semuabarangpobeli] != 0:
                    raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Maksimum 1 PO 1 barang yang ditukar!"))
        else:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Tukar Barang hanya bisa dengan PO Pembelian dari Macrocitra Multicheck!"))    

    # JUMLAH BARANG SJ DETIL DIPASTIKAN SAMA DENGAN STOK KELUAR
    for semuasj in thisObj.penjualansj:
        listbarang2 = {}
        for semuasjdetil in semuasj.penjualansjdetil:
            if semuasjdetil.namaproduk in listbarang2:
                listbarang2[semuasjdetil.namaproduk] += semuasjdetil.jumlah
            else:
                listbarang2[semuasjdetil.namaproduk] = semuasjdetil.jumlah
        
        for semuastokkeluar in semuasj.stokkeluar:
            if semuastokkeluar.namaproduk in listbarang2:
                listbarang2[semuastokkeluar.namaproduk] -= semuastokkeluar.jumlah
            else:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Barang yang keluar dan yang didaftarkan tidak sesuai!"))
        
        for semualistbarang2 in listbarang2:
            if listbarang2[semualistbarang2] != 0:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Jumlah Produk : " + str(semualistbarang2.namaproduk) + " yang Akan Dikeluarkan Tidak Sesuai. Selisih : " + str(listbarang2[semualistbarang2])))
    
    return True

def validasipenjualansj(self,cr,uid,id,context=None):
    hasil={}
    listproduk = {}
    listproduk2 = {}
    objini = self.browse(cr,uid,id)
    # SJDETIL
    # 1. Pastikan jumlah yang ada di SJ tidak melebihi pesanan, dan barang tersebut ada di SJ!
    #    Browse diri sendiri, buat list ['nopodetil' : 'jumlahpesanan'], Iterasi seluruh sj, tiap Detil dengan produk sama mengurangi jumlah ke list.
    # 2. Pastikan LIFO otomatis sesuai jumlahnya dengan yang dipesan
    for semuaprodukpo in objini.idpenjualanpo.penjualanpodetil:
        listproduk[semuaprodukpo] = semuaprodukpo.jumlah

    for semuasj in objini.idpenjualanpo.penjualansj:
        for semuasjdetil in semuasj.penjualansjdetil:
            #Cek Barang yang Di SJ BENAR ATAU TIDAK, KALAU BENAR KURANGI BARANG YANG BERSANGKUTAN
            if semuasjdetil.pilihanproduk in listproduk:
                listproduk[semuasjdetil.pilihanproduk] -= semuasjdetil.jumlah
            else:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Produk tidak terdaftar!"))    
        # Cek barang tidak jadi negatif stoknya
        for semuastokkeluar in semuasj.stokkeluar:
            saldo = semuastokkeluar.idstok.debit
            for semuastokkeluar2 in semuastokkeluar.idstok.stokkeluar:
                saldo -= semuastokkeluar2.jumlah 
            if    saldo < 0:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Stok yang Keluar melebihi yang ada! (Selisih: " + str(saldo) + " )"))            
    
    for semuaproduk in listproduk:
        if listproduk[semuaproduk] < 0:
            notes = ""
            if semuaproduk.notes != False:
                notes = str(semuaproduk.notes)
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Jumlah Produk: " + semuaproduk.merk.merk + " " + semuaproduk.namaproduk.namaproduk + " " + notes + " Melebihi Yang Dibeli" + " (Pesan:" + str(semuaproduk.jumlah) + ", Datang:" + str(semuaproduk.jumlah - listproduk[semuaproduk]) + ")"))                        
    
    if len(objini.penjualansjdetil) > 0:
        for semuapenjualansjdetil in objini.penjualansjdetil:
            if semuapenjualansjdetil.namaproduk in listproduk2:
                listproduk2[semuapenjualansjdetil.namaproduk] += semuapenjualansjdetil.jumlah
            else:
                listproduk2[semuapenjualansjdetil.namaproduk] = semuapenjualansjdetil.jumlah
        
        for semuastokkeluar in objini.stokkeluar:
            if semuastokkeluar.namaproduk in listproduk2:
                listproduk2[semuastokkeluar.namaproduk] -= semuastokkeluar.jumlah
            else:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Produk : " + str(semuastokkeluar.namaproduk) + " Belum Didaftarkan Pada List Barang pada SJ"))                        
        
        for semualistproduk2 in listproduk2:
            if     listproduk2[semualistproduk2] != 0:
                raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Jumlah Produk : " + str(semualistproduk2.namaproduk) + " yang Akan Dikeluarkan Tidak Sesuai. Selisih : " + str(listproduk2[semualistproduk2])))
        
    return True

def validasipenjualanfaktur(self,cr,uid,id,context=None):
    objini = self.browse(cr,uid,id)
    #Cek SJ akan difaktur ulang
    listsj = []
    for semuafaktur in objini.idpenjualanpo.penjualanfaktur:
        if semuafaktur.penjualansj in listsj and semuafaktur.penjualansj.nomorsj != False:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'),_("Sudah Ada Faktur dengan Surat Jalan: "+ str(semuafaktur.penjualansj.nomorsj)))    
        else:
            listsj.append(semuafaktur.penjualansj)
            
    return True                
