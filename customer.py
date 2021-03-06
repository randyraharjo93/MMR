from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools,api
import datetime
import itertools

class mmr_customer(osv.osv):
    _name = "mmr.customer"
    _description = "Modul customer untuk PT. MMR."
    _rec_name = "kode"

    # Hitung Total Hutang yang dipunya customer
    def _hitung_hutang(self, cr, uid, ids, field_name, arg, context):
        res = {}
        popenjualanClass = self.pool.get("mmr.penjualanpo")
        pembayaranpenjualandetilClass = self.pool.get("mmr.pembayaranpenjualandetil")
        for customer in self.browse(cr,uid,ids):
            total = 0
            for semuapo in popenjualanClass.browse(cr,uid,popenjualanClass.search(cr,uid,[('customer','=',customer.id)])):
                for semuafaktur in semuapo.penjualanfaktur:
                    total+=semuafaktur.netto
            for semuapembayaran in pembayaranpenjualandetilClass.browse(cr,uid,pembayaranpenjualandetilClass.search(cr,uid,[('customer','=',customer.id)])):
                total-=semuapembayaran.bayar
            res[customer.id] = total
        return res

    _columns = {
        'kode': fields.char("Kode", required=True, size=15),
        'nama': fields.char("Nama", required=True, size=27),
        'alamat': fields.char("Alamat", size=60),
        'rayon': fields.many2one("mmr.rayon", "Rayon", required=True, domain="[('aktif', '=', True)]"),
        'kota': fields.many2one("mmr.kota", "Kota", required=True),
        'telp': fields.char("Telepon"),
        'hutang': fields.function(_hitung_hutang, type="float", method=True, string="Hutang", digits=(12,2)),
        'npwp': fields.char("NPWP"),
        'batashutang': fields.float("Batas Hutang", digits=(12,2)),
        'syaratpembayaran': fields.many2one("mmr.syaratpembayaran", "Syarat Pembayaran"),
        'listrekening': fields.one2many("mmr.nomorrekening", "customer", "List Rekening"),
        'listcp': fields.one2many("mmr.cp", "customer", "List CP"),
        'laporansales' : fields.one2many("mmr.laporansales", "customer", "Laporan Sales"),
        'notes' : fields.text("Notes"),
    }

    def create(self,cr,uid,vals,context=None):
        id = super(mmr_customer,self).create(cr,uid,vals,context)

        validasicustomer(self,cr,uid,id)
        return id

    def write(self,cr,uid,ids,vals,context=None):
        super(mmr_customer,self).write(cr, uid, ids, vals, context=context)

        validasicustomer(self,cr,uid,ids)
        return super(mmr_customer,self).write(cr, uid, ids, vals, context=context)

    _defaults = {
                'batashutang' : 10000000,
                }

mmr_customer()

class mmr_kota(osv.osv):
    _name = "mmr.kota"
    _description = "Modul kota untuk PT. MMR."
    _rec_name = "nama"

    # Hitung total penjualan kota bulan berjalan
    def _isi_pencapaian(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for kota in self.browse(cr,uid,ids):
            total = 0
            for semuapo in kota.listpopenjualan:
                for semuafaktur in semuapo.penjualanfaktur:
                    if datetime.datetime.strptime(semuafaktur.tanggalterbit,'%Y-%m-%d').strftime("%m") == datetime.datetime.today().strftime("%m"):
                        total+=semuafaktur.hppembelian
            res[kota.id] = total
        return res

    _columns = {
        'nama': fields.char("Nama", required=True),
        'listcustomer': fields.one2many("mmr.customer", "kota","List Customer", readonly=True),
        'listpopenjualan' : fields.one2many("mmr.penjualanpo","kota","List Penjualan PO"),
        'pencapaian': fields.function(_isi_pencapaian,string="Pencapaian Bulan Ini",method=True,type="float", digits=(12,2)),
        'laporansales' : fields.one2many("mmr.laporansales","kota","Laporan Sales"),
        'notes' : fields.text("Notes"),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(nama)', 'Kota Sudah Ada!')
    ]

mmr_kota()

class mmr_rayon(osv.osv):
    _name = "mmr.rayon"
    _description = "Modul rayon untuk PT. MMR."
    _rec_name = "display_name"

    # Hitung total penjualan rayon bulan berjalan
    def _isi_pencapaian(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for rayon in self.browse(cr,uid,ids):
            total = 0
            for semuapo in rayon.listpopenjualan:
                for semuafaktur in semuapo.penjualanfaktur:
                    if datetime.datetime.strptime(semuafaktur.tanggalterbit,'%Y-%m-%d').strftime("%m") == datetime.datetime.today().strftime("%m"):
                        total+=semuafaktur.hppembelian
            res[rayon.id] = total
        return res

    def _isi_pencapaian_kumulatif(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for rayon in self.browse(cr,uid,ids):
            total = 0
            rayon_ids = self.search(cr,uid,["|",('id', 'child_of', [rayon.id]),('id', '=', rayon.id)])
            for semuarayon in self.browse(cr,uid,rayon_ids):
                for semuapo in semuarayon.listpopenjualan:
                    for semuafaktur in semuapo.penjualanfaktur:
                        if datetime.datetime.strptime(semuafaktur.tanggalterbit,'%Y-%m-%d').strftime("%m") == datetime.datetime.today().strftime("%m"):
                            total+=semuafaktur.hppembelian
            res[rayon.id] = total
        return res

    # Target Kumulatif
    def _isi_target_kumulatif(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for rayon in self.browse(cr,uid,ids):
            total = 0
            rayon_ids = self.search(cr,uid,["|",('id', 'child_of', [rayon.id]),('id', '=', rayon.id)])
            for semuarayon in self.browse(cr,uid,rayon_ids):
                total+=semuarayon.target
            res[rayon.id] = total
        return res

    # Buat display Name
    def _get_display_name(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for rayon in self.browse(cr,uid,ids):
            kode = rayon.kode or "-"
            periode = rayon.periode or "Non Periodic"
            res[rayon.id] = kode + " " + periode
        return res

    _columns = {
        'kode': fields.char("Kode", required=True),
        'listcustomer': fields.one2many("mmr.customer", "rayon","List Customer", readonly=True),
        'listpopenjualan' : fields.one2many("mmr.penjualanpo","rayon","List Penjualan PO"),
        'listsales' : fields.many2many("mmr.sales","rayon_sales","listsales","listrayon","List Sales"),
        'target': fields.float("Target", digits=(12,2)),
        'targetkumulatif': fields.function(_isi_target_kumulatif, type="float", method=True, string="Target Kumulatif"),
        'pencapaian': fields.function(_isi_pencapaian,string="Pencapaian Bulan Ini",method=True,type="float", digits=(12,2)),
        'pencapaiankumulatif': fields.function(_isi_pencapaian_kumulatif,string="Pencapaian Kumulatif Bulan Ini",method=True,type="float", digits=(12,2)),
        'laporansales' : fields.one2many("mmr.laporansales","rayon","Laporan Sales"),
        'notes' : fields.text("Notes"),
        'periode': fields.char("Periode", required=True),
        'aktif': fields.boolean("Aktif"),
        'display_name': fields.function(_get_display_name, type="char", method=True, string="Nama"),
        'parent_id': fields.many2one("mmr.rayon", string="Parent Rayon")
    }

    _defaults = {
                'aktif' : True,
                }

mmr_rayon()


class mmr_rayon_dummy(osv.osv_memory):
    _name = "mmr.rayon_dummy"
    _description = "Modul rayon dummy untuk PT. MMR."
    _rec_name = "display_name"

    # Hitung total penjualan rayon bulan berjalan
    @api.depends('listpopenjualan')
    def _isi_pencapaian(self):
        for rayon in self:
            total = 0
            for semuapo in rayon.listpopenjualan:
                for semuafaktur in semuapo.penjualanfaktur:
                    total += semuafaktur.hppembelian
            rayon.pencapaian = total

    # Hitung total penjualan rayon bulan berjalan
    @api.onchange('listcustomer')
    def _isi_penjualanpo(self):
        for rayon in self:
            penjualan_po_ids = []
            for listcustomer in rayon.listcustomer:
                penjualan_po_ids += self.env['mmr.penjualanpo'].search([('customer', '=', listcustomer.id)]).ids
            rayon.listpopenjualan = [(6, 0, penjualan_po_ids)]

    # Hitung total penjualan rayon bulan berjalan
    @api.onchange('listkota')
    def _isi_customer(self):
        for rayon in self:
            cust_ids = []
            for listkota in rayon.listkota:
                cust_ids += self.env['mmr.customer'].search([('kota', '=', listkota.id)]).ids
            rayon.listcustomer = [(6, 0, cust_ids)]

    # Buat display Name
    def _get_display_name(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for rayon in self.browse(cr, uid, ids):
            kode = rayon.kode or "-"
            periode = rayon.periode or "Non Periodic"
            res[rayon.id] = kode + " " + periode
        return res

    _columns = {
        'kode': fields.char("Kode", required=True),
        'listkota': fields.many2many("mmr.kota", "rayon_dummy_kota_rel", "rayon_dummy_id", "kota_id", "List Kota"),
        'listcustomer': fields.many2many("mmr.customer", "rayon_dummy_customer_rel", "rayon_dummy_id", "customer_id", "List Customer"),
        'listpopenjualan': fields.many2many("mmr.penjualanpo", "rayon_dummy_penjualan_rel", "rayon_dummy_id", "penjualan", "List Penjualan PO"),
        'listsales': fields.many2many("mmr.sales", "rayon_sales", "listsales", "listrayon", "List Sales"),
        'target': fields.float("Target", digits=(12, 2)),
        'pencapaian': fields.float(compute=_isi_pencapaian, string="Total Pencapaian", digits=(12, 2)),
        'notes': fields.text("Notes"),
        'display_name': fields.function(_get_display_name, type="char", method=True, string="Nama"),
        'simulasi_rayon_id': fields.many2one("mmr.simulasi_rayon", "simulasi rayon"),
    }

mmr_rayon_dummy()


class mmr_template_rayon(osv.osv):
    _name = "mmr.template_rayon"
    _description = "Modul template rayon untuk PT. MMR."

    @api.multi
    def terapkanrayon(self):
        for template_rayon in self:
            for rayon in template_rayon.rayon_ids:
                rayon_baru_id = self.env['mmr.rayon'].create({'kode': rayon.kode, 'periode': template_rayon.name, 'target': rayon.target})
                for customer in rayon.listcustomer:
                    customer.rayon = rayon_baru_id
                for sales in rayon.listsales:
                    sales.rayon = rayon_baru_id

    _columns = {
        'name': fields.char("Periode", required=True),
        'aktif': fields.boolean("Aktif", readonly=True),
        'rayon_ids': fields.many2many('mmr.rayon_dummy', 'template_rayon_rayon_dummy_rel', 'rayon_dummy_id', 'template_id', 'Rayon'),
    }

mmr_template_rayon()


class simulasi_rayon(osv.osv_memory):
    # Pada wizard buat tombol untuk ciptakan template rayon baru berdasarkan nama yang dimasukkan pada field name
    _name = 'mmr.simulasi_rayon'
    _description = 'Simulasi Rayon'

    @api.onchange('template_rayon')
    def onchange_template_rayon(self):
        # Isi rayon asal(dummy) dengan value yang mirip dengan rayon.
        list_rayon = []
        for rayon_id in self.template_rayon.rayon_ids:
            kota_ids = []
            total_penjualan = 0
            for customer in rayon_id.listcustomer:
                if customer.kota.id not in kota_ids:
                    kota_ids.append(customer.kota.id)
                for penjualan_po_id in self.env['mmr.penjualanpo'].search([('customer', '=', customer.id)]):
                    for semuafaktur in penjualan_po_id.penjualanfaktur:
                        total_penjualan += semuafaktur.hppembelian
            list_rayon += [(0, 0, {
                'kode': rayon_id.kode,
                'listkota': self.env['mmr.kota'].browse(kota_ids),
                'listcustomer': rayon_id.listcustomer,
                'listpopenjualan': rayon_id.listpopenjualan,
                'listsales': rayon_id.listsales,
                'target': rayon_id.target,
                'pencapaian': total_penjualan,
                })]
        self.rayon = list_rayon

    @api.multi
    def buatrayon(self):
        for simulasi_rayon in self:
            self.env['mmr.template_rayon'].create({'name': simulasi_rayon.name,
                'rayon_ids': [(6, 0, simulasi_rayon.rayon.ids)]})


    _columns = {
        'name': fields.char('Nama Periode Baru'),
        'template_rayon': fields.many2one('mmr.template_rayon', "Template Asal"),
        'rayon': fields.one2many('mmr.rayon_dummy', "simulasi_rayon_id", 'Rayon'),
    }

simulasi_rayon()


# !Deprecated!
class mmr_daftarhargacustomer(osv.osv):
    _name = "mmr.daftarhargacustomer"
    _description = "Modul daftar harga customer untuk PT. MMR."

    @api.one
    @api.depends("diskon","harga")
    def _hitung_netto(self):
        self.netto = round(self.harga - (self.harga * self.diskon / 100),2)


    _columns = {
        'namaproduk': fields.many2one("mmr.produk", "Nama Produk", readonly=True),
        'customer': fields.many2one("mmr.customer", "Customer", required=True),
        'harga': fields.float("Harga", required=True, digits=(12,2)),
        'diskon': fields.float("Diskon(%)", digits=(12,2)),
        'netto': fields.float("Netto", compute="_hitung_netto", store=True, digits=(12,2)),
        'tanggalefektif': fields.datetime("Tanggal Efektif", required=True),
        'notes' : fields.text("Notes")
    }

    def create(self,cr,uid,vals,context=None):
        id = super(mmr_daftarhargacustomer,self).create(cr,uid,vals,context)

        validasidaftarhargacustomer(self,cr,uid,id)
        return id

    def write(self,cr,uid,ids,vals,context=None):
        super(mmr_daftarhargacustomer,self).write(cr, uid, ids, vals, context=context)

        validasidaftarhargacustomer(self,cr,uid,ids)
        return super(mmr_daftarhargacustomer,self).write(cr, uid, ids, vals, context=context)

mmr_daftarhargacustomer()

def validasicustomer(self,cr,uid,id,context=None):

    thisObj = self.browse(cr,uid,id)
    searchIds = self.search(cr,uid,['|',('nama','=',thisObj.nama),('kode','=',thisObj.kode)])

    # Apabila ada lebih dari satu data yang sama, maka stop proses
    if len(searchIds)>1:
        raise osv.except_osv(_('Tidak Dapat Membuat'),_("Customer Sudah Terdaftar!"))
    return True

# !Deprecated!
def validasidaftarhargacustomer(self,cr,uid,id,context=None):

    thisObj = self.browse(cr,uid,id)

    # Jika parent minimal jual > harga jual ini, warning
    if thisObj.namaproduk.hargajualterendah > thisObj.netto:
        raise osv.except_osv(_('Tidak Dapat Membuat'),_("Harga Jual Dibawah Harga Jual Minimum!"))
    return True
