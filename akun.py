from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools, api
import datetime
import time
from dateutil.relativedelta import relativedelta
import itertools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


class mmr_akun(osv.osv):
    _name = "mmr.akun"
    _description = "Modul akun untuk PT. MMR."
    _rec_name = "namaakun"

    # Hitung Total debit akun, apabila normal di debit
    # Apabila tidak normal di debit, isi dengan 0
    def _hitung_debit(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for semuaakun in self.browse(cr, uid, ids):
            if semuaakun.normaldi == "debit":
                nilai = 0
                for semuaakundetil in semuaakun.akundetil:
                    nilai += semuaakundetil.debit
                    nilai -= semuaakundetil.kredit
                res[semuaakun.id] = nilai
            elif semuaakun.normaldi == "debitkredit":
                nilai = 0
                for semuaakundetil in semuaakun.akundetil:
                    nilai += semuaakundetil.debit
                res[semuaakun.id] = nilai
            else:
                res[semuaakun.id] = 0

        return res

    # Hitung Total debit akun, apabila normal di kredit
    # Apabila tidak normal di kredit, isi dengan 0
    def _hitung_kredit(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for semuaakun in self.browse(cr, uid, ids):
            if semuaakun.normaldi == "kredit":
                nilai = 0
                for semuaakundetil in semuaakun.akundetil:
                    nilai -= semuaakundetil.debit
                    nilai += semuaakundetil.kredit
                res[semuaakun.id] = nilai
            elif semuaakun.normaldi == "debitkredit":
                nilai = 0
                for semuaakundetil in semuaakun.akundetil:
                    nilai += semuaakundetil.kredit
                res[semuaakun.id] = nilai
            else:
                res[semuaakun.id] = 0
        return res

    _columns = {
        'idakunparent': fields.selection([('activa', '1. Activa'), ('hutang', '2. Hutang'), ('modal', '3. Modal'), ('penjualan', '4. Penjualan'), ('pembelian', '5. Pembelian'), ('biaya', '6. Biaya'), ('pendapatandiluarusaha', '7. Pendapatan di Luar Usaha'), ('bebandiluarusaha', '8. Beban di Luar Usaha')], "Golongan", required=True),
        'nomorakun': fields.char("Nomor Akun", required=True),
        'namaakun': fields.char("Nama Akun", required=True),
        'debit': fields.function(_hitung_debit, type="float", method=True, string="Debit", digits=(12, 2)),
        'kredit': fields.function(_hitung_kredit, type="float", method=True, string="Kredit", digits=(12, 2)),
        'akundetil': fields.one2many("mmr.akundetil", "idakun", "History"),
        'notes': fields.text("Notes"),
        'normaldi': fields.selection([('debit', 'Debit'), ('kredit', 'Kredit'), ('debitkredit', 'Debit Kredit')], "Normal Di", required=True),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(nomorakun)', 'Nomor Akun Sudah Ada!')
    ]

mmr_akun()

class mmr_akundetil(osv.osv):
    _name = "mmr.akundetil"
    _description = "Modul akun detil untuk PT. MMR."

    # Isi nilai debit / kredit berdasarkan sumber akundetil-nya
    # Apabila tidak bersumnber, isi berdasarkan field isidebit / isikredit
    @api.one
    @api.depends("idakun.normaldi",
                "sumberpembelianfaktur.bruto", "sumberpembelianfaktur.diskon", "sumberpembelianfaktur.pajak", "sumberpembelianfaktur.biayalain",
                "sumberpembelianfaktur.netto", "sumberpembelianfaktur.hppembelian",
                "sumberpenjualanfaktur.bruto", "sumberpenjualanfaktur.diskon", "sumberpenjualanfaktur.pajak", "sumberpenjualanfaktur.biayalain",
                "sumberpenjualanfaktur.netto", "sumberpenjualanfaktur.hppembelian",
                "sumberpembayaranpembelian.bayar", "sumberpembayaranpenjualan.bayar",
                "sumberbiaya.jumlahbiaya", "isidebit", "isikredit")
    def _ambil_nilai(self):
        if self.idakun:
            if self.sumberpembelianfaktur and self.sumberpembelianfaktur.akunotomatis != False:
                data = {'bruto': self.sumberpembelianfaktur.bruto, 'diskon': self.sumberpembelianfaktur.diskon,
                    'pajak': self.sumberpembelianfaktur.pajak, 'biayalain': self.sumberpembelianfaktur.biayalain,
                    'netto': self.sumberpembelianfaktur.netto, 'hppembelian': self.sumberpembelianfaktur.hppembelian}
                for semuaaturanjurnal in self.sumberpembelianfaktur.aturanakun.aturanakundetil:
                    if semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "debit":
                        self.debit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpembelianfaktur.write_date
                    elif semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "kredit":
                        self.kredit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpembelianfaktur.write_date
            elif self.sumberpenjualanfaktur and self.sumberpenjualanfaktur.akunotomatis != False:
                data = {'bruto': self.sumberpenjualanfaktur.bruto, 'diskon': self.sumberpenjualanfaktur.diskon,
                    'pajak': self.sumberpenjualanfaktur.pajak, 'biayalain': self.sumberpenjualanfaktur.biayalain, 'netto': self.sumberpenjualanfaktur.netto, 'hppembelian': self.sumberpenjualanfaktur.hppembelian}
                for semuaaturanjurnal in self.sumberpenjualanfaktur.aturanakun.aturanakundetil:
                    if semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "debit":
                        self.debit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpenjualanfaktur.write_date
                    elif semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "kredit":
                        self.kredit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpenjualanfaktur.write_date
            elif self.sumberpembayaranpembelian and self.sumberpembayaranpembelian.akunotomatis != False:
                data = {'bayar': self.sumberpembayaranpembelian.bayar, 'hutang': self.sumberpembayaranpembelian.hutang, 'kelebihan': self.sumberpembayaranpembelian.kelebihan, 'kekurangan': self.sumberpembayaranpembelian.kekurangan, 'biayatransfer': self.sumberpembayaranpembelian.biayatransfer, 'biayalain': self.sumberpembayaranpembelian.biayalain, 'bayartotal': self.sumberpembayaranpembelian.bayartotal}
                for semuaaturanjurnal in self.sumberpembayaranpembelian.aturanakun.aturanakundetil:
                    if semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "debit":
                        self.debit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpembelianfaktur.write_date
                    elif semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "kredit":
                        self.kredit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpembelianfaktur.write_date
            elif self.sumberpembayaranpenjualan and self.sumberpembayaranpenjualan.akunotomatis != False:
                data = {'bayar': self.sumberpembayaranpenjualan.bayar, 'hutang': self.sumberpembayaranpenjualan.hutang, 'kelebihan': self.sumberpembayaranpenjualan.kelebihan, 'kekurangan': self.sumberpembayaranpenjualan.kekurangan, 'biayatransfer': self.sumberpembayaranpenjualan.biayatransfer, 'biayalain': self.sumberpembayaranpenjualan.biayalain, 'bayartotal': self.sumberpembayaranpenjualan.bayartotal}
                for semuaaturanjurnal in self.sumberpembayaranpenjualan.aturanakun.aturanakundetil:
                    if semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "debit":
                        self.debit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpembelianfaktur.write_date
                    elif semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "kredit":
                        self.kredit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpembelianfaktur.write_date
            elif self.sumberbiaya and self.sumberbiaya.akunotomatis != False:
                data = {'jumlahbiaya': self.sumberbiaya.jumlahbiaya}
                for semuaaturanjurnal in self.sumberbiaya.aturanakun.aturanakundetil:
                    if semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "debit":
                        self.debit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpembelianfaktur.write_date
                    elif semuaaturanjurnal.noakun == self.idakun and semuaaturanjurnal.debitkredit == "kredit":
                        self.kredit = data[semuaaturanjurnal.field.name]
                        self.tanggal = self.sumberpembelianfaktur.write_date
            elif self.sumberpembelianfaktur and not self.sumberpembelianfaktur.akunotomatis:
                self.debit = self.isidebit
                self.kredit = self.isikredit
            elif self.sumberpembayaranpembelian and not self.sumberpembayaranpembelian.akunotomatis:
                self.debit = self.isidebit
                self.kredit = self.isikredit
            else:
                self.debit = self.isidebit
                self.kredit = self.isikredit

    # Tampilkan sumber dengan tulisan yang baik.
    @api.multi
    @api.depends("sumberpembelianfaktur", "sumberpembelianfaktur.nomorfaktur", "sumberpenjualanfaktur", "sumberpenjualanfaktur.nomorfaktur",
                "sumberpembayaranpembelian", "sumberpembayaranpembelian.supplier", "sumberpembayaranpembelian.supplier.nama",
                "sumberpembayaranpenjualan", "sumberpembayaranpenjualan.customer", "sumberpembayaranpenjualan.customer.nama",
                "sumberkegiatanakunting", "sumberkegiatanakunting.detilkejadian", "sumberbiaya", "sumberbiaya.detilkejadian",
                "sumberinventaris", "sumberinventaris.nama", "sumberjurnalpenyesuaian", "sumberjurnalpenyesuaian.tanggal",
                "sumberjurnalpenutup", "sumberjurnalpenutup.tanggal")
    def _get_sumber(self):
        for semuaakundetil in self:
            if semuaakundetil.sumberpembelianfaktur:
                semuaakundetil.sumber = "Faktur Nomor : " + str(semuaakundetil.sumberpembelianfaktur.nomorfaktur)
            elif semuaakundetil.sumberpenjualanfaktur:
                semuaakundetil.sumber = "Faktur Nomor : " + str(semuaakundetil.sumberpenjualanfaktur.nomorfaktur)
            elif semuaakundetil.sumberpembayaranpembelian:
                semuaakundetil.sumber = "Pembayaran Pembelian Untuk : " + semuaakundetil.sumberpembayaranpembelian.supplier.nama
            elif semuaakundetil.sumberpembayaranpenjualan:
                semuaakundetil.sumber = "Pembayaran Penjualan Untuk : " + semuaakundetil.sumberpembayaranpenjualan.customer.nama
            elif semuaakundetil.sumberkegiatanakunting:
                semuaakundetil.sumber = "Kegiatan Akunting : " + str(semuaakundetil.sumberkegiatanakunting.detilkejadian)
            elif semuaakundetil.sumberbiaya:
                semuaakundetil.sumber = "Biaya : " + str(semuaakundetil.sumberbiaya.detilkejadian)
            elif semuaakundetil.sumberinventaris:
                semuaakundetil.sumber = "Inventaris : " + str(semuaakundetil.sumberinventaris.nama)
            elif semuaakundetil.sumberjurnalpenyesuaian:
                semuaakundetil.sumber = "Jurnal Penyesuaian : " + str(semuaakundetil.sumberjurnalpenyesuaian.tanggal)
            elif semuaakundetil.sumberjurnalpenutup:
                semuaakundetil.sumber = "Jurnal Penutup : " + str(semuaakundetil.sumberjurnalpenutup.tanggal)
            elif semuaakundetil.sumberjurnalringkasan:
                semuaakundetil.sumber = "Jurnal Peringkas : bulan: " + str(semuaakundetil.sumberjurnalringkasan.bulan) + ", tahun: " + str(semuaakundetil.sumberjurnalringkasan.tahun)

    # Ambil tanggal berdasarkan sumber
    @api.multi
    @api.depends("sumberpembelianfaktur", "sumberpembelianfaktur.tanggalterbit", "sumberpenjualanfaktur", "sumberpenjualanfaktur.tanggalterbit", "sumberpembayaranpembelian", "sumberpembayaranpembelian.tanggalbayar", "sumberpembayaranpenjualan", "sumberpembayaranpenjualan.tanggalbayar", "sumberkegiatanakunting", "sumberkegiatanakunting.tanggal", "sumberbiaya", "sumberbiaya.tanggal", "sumberinventaris", "sumberinventaris.tanggal", "sumberjurnalpenyesuaian", "sumberjurnalpenyesuaian.tanggal", "sumberjurnalpenutup", "sumberjurnalpenutup.tanggal", "sumberjurnalringkasan", "sumberjurnalringkasan.bulan", "sumberjurnalringkasan.tahun")
    def _ambil_tanggal(self):
        for semuaakun in self:
            if semuaakun.sumberpembelianfaktur:
                semuaakun.tanggal = semuaakun.sumberpembelianfaktur.tanggalterbit
            elif semuaakun.sumberpenjualanfaktur:
                semuaakun.tanggal = semuaakun.sumberpenjualanfaktur.tanggalterbit
            elif semuaakun.sumberpembayaranpembelian:
                semuaakun.tanggal = semuaakun.sumberpembayaranpembelian.tanggalbayar
            elif semuaakun.sumberpembayaranpenjualan:
                semuaakun.tanggal = semuaakun.sumberpembayaranpenjualan.tanggalbayar
            elif semuaakun.sumberkegiatanakunting:
                semuaakun.tanggal = semuaakun.sumberkegiatanakunting.tanggal
            elif semuaakun.sumberbiaya:
                semuaakun.tanggal = semuaakun.sumberbiaya.tanggal
            elif semuaakun.sumberinventaris:
                semuaakun.tanggal = semuaakun.sumberinventaris.tanggal
            elif semuaakun.sumberjurnalpenyesuaian:
                semuaakun.tanggal = semuaakun.sumberjurnalpenyesuaian.tanggal
            elif semuaakun.sumberjurnalpenutup:
                semuaakun.tanggal = semuaakun.sumberjurnalpenutup.tanggal
            elif semuaakun.sumberjurnalringkasan:
                tanggalperingkasan = "01" + semuaakun.sumberjurnalringkasan.bulan + semuaakun.sumberjurnalringkasan.tahun
                semuaakun.tanggal = datetime.datetime.strptime(tanggalperingkasan, "%d%m%Y").date()

    _columns = {
        'idakun': fields.many2one("mmr.akun", "Nama Akun"),
        'tanggal': fields.date("Waktu", compute="_ambil_tanggal"),
        'sumberpembelianfaktur': fields.many2one("mmr.pembelianfaktur", "Sumber Pembelian Faktur", ondelete='cascade'),
        'sumberpenjualanfaktur': fields.many2one("mmr.penjualanfaktur", "Sumber Penjualan Faktur", ondelete='cascade'),
        'sumberpembayaranpembelian': fields.many2one("mmr.pembayaranpembelian", "Sumber Pembayaran Pembelian", ondelete='cascade'),
        'sumberpembayaranpenjualan': fields.many2one("mmr.pembayaranpenjualan", "Sumber Pembayaran Penjualan", ondelete='cascade'),
        'sumberkegiatanakunting': fields.many2one("mmr.kegiatanakunting", "Sumber Kegiatan Akunting", ondelete='cascade'),
        'sumberbiaya': fields.many2one("mmr.biaya", "Sumber Biaya", ondelete='cascade'),
        'sumberinventaris': fields.many2one("mmr.inventaris", "Sumber Inventaris", ondelete='cascade'),
        'sumberjurnalpenyesuaian': fields.many2one("mmr.jurnalpenyesuaian", "Sumber Jurnal Penyesuaian", ondelete='cascade'),
        'sumberjurnalpenutup': fields.many2one("mmr.jurnalpenutup", "Sumber Jurnal Penutup", ondelete='cascade'),
        'sumberjurnalringkasan': fields.many2one("mmr.autodelete", "Sumber Jurnal Peringkas", ondelete='cascade'),
        'sumber': fields.char("Sumber", compute="_get_sumber"),
        'debit': fields.float("Debit", compute="_ambil_nilai", digits=(12, 2)),
        'isidebit': fields.float("Ubah Debit", digits=(12, 2)),
        'kredit': fields.float("Kredit", compute="_ambil_nilai", digits=(12, 2)),
        'isikredit': fields.float("Ubah Kredit", digits=(12, 2)),
        'notes': fields.text("Notes"),
    }

mmr_akundetil()


class mmr_saveakun(osv.osv):
    _name = "mmr.saveakun"
    _rec_name = 'tanggal'

    _columns = {
        'tanggal': fields.date('Tanggal Simpan Nilai Akun'),
        'idssaveakun': fields.one2many('mmr.saveakundetil', 'idsaveakun', 'List Akun')
    }


class mmr_saveakundetil(osv.osv):
    _name = "mmr.saveakundetil"

    _columns = {
        'idsaveakun': fields.many2one('mmr.saveakun'),
        'idakun': fields.many2one('mmr.akun', 'Nama Akun'),
        'nomorakun': fields.char('Nomor Akun', related="idakun.nomorakun"),
        'debit': fields.float("Debit", digits=(12, 2)),
        'kredit': fields.float("Kredit", digits=(12, 2)),
    }


class mmr_jurnalpenyesuaian(osv.osv):
    
    # Wadah Penjurnalan Penyesuaian
    
    _name = "mmr.jurnalpenyesuaian"
    _description = "Modul Jurnal Penyesuaian untuk PT. MMR."
    
    # Isi status jurnal. Apakah balance / tidak
    def _set_status(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        res = {}
        for jurnalpenyesuaian in self.browse(cr, uid, ids):
            res[jurnalpenyesuaian.id]    = "Normal"
            total = 0    
            for semuaakundetil in jurnalpenyesuaian.akunterkena:
                total+=semuaakundetil.debit
                total-=semuaakundetil.kredit
            if round(total, 2)!=0:
                res[jurnalpenyesuaian.id]    = "Jurnal Tidak Balance"
                
        return res
    
    # Isi tanggal, secara otomatis akhir bulan
    def onchange_tanggal(self, cr, uid, ids, bulan, tahun, context=None):
        res = {}
        if bulan and tahun:
            tanggal = False
            if int(bulan) == 12:
                tanggal = datetime.date(int(tahun)+1, 1, 1)
            else:
                tanggal = datetime.date(int(tahun), int(bulan)+1, 1)    
            res['tanggal'] =  tanggal - datetime.timedelta(days=1)
            
        return {'value': res}    
    
    _columns = {
        'bulan' : fields.selection([('01', 'Januari'), ('02', 'Februari'), ('03', 'Maret')
                                        , ('04', 'April'), ('05', 'Mei'), ('06', 'Juni'), ('07', 'Juli')
                                        , ('08', 'Agustus'), ('09', 'September'), ('10', 'Oktober'), ('11', 'November')
                                        , ('12', 'Desember')], "Bulan", required=True), 
        'tahun' : fields.selection([('2015', '2015'), ('2016', '2016'), ('2017', '2017')
                                        , ('2018', '2018'), ('2019', '2019'), ('2020', '2020'), ('2021', '2021')
                                        , ('2022', '2022'), ('2023', '2023'), ('2024', '2024'), ('2025', '2025')], "Tahun", required=True), 
        'tanggal' : fields.date("Tanggal Penyesuaian"), 
        'akunterkena': fields.one2many("mmr.akundetil", "sumberjurnalpenyesuaian", "Jurnal"), 
        'status' : fields.function(_set_status, type="char", method=True, string="Status"), 
        'notes' : fields.text("Notes"), 
    }
    
    def create(self, cr, uid, vals, context=None):
        id = super(mmr_jurnalpenyesuaian, self).create(cr, uid, vals, context)
        validasijurnalpenyesuaian(self, cr, uid, id)
        return id
    
    def write(self, cr, uid, ids, vals, context=None):
        super(mmr_jurnalpenyesuaian, self).write(cr, uid, ids, vals, context=context)
        validasijurnalpenyesuaian(self, cr, uid, ids)
        return super(mmr_jurnalpenyesuaian, self).write(cr, uid, ids, vals, context=context)
    
mmr_jurnalpenyesuaian()

class mmr_jurnalpenutup(osv.osv):
    
    # Wadah Penjurnalan Penutupan
    
    _name = "mmr.jurnalpenutup"
    _description = "Modul Jurnal Penutup untuk PT. MMR."
    
    # Isi status jurnal. Apakah balance / tidak
    def _set_status(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        res = {}
        for jurnalpenutup in self.browse(cr, uid, ids):
            res[jurnalpenutup.id] = "Normal"
            total = 0
            for semuaakundetil in jurnalpenutup.akunterkena:
                total += semuaakundetil.debit
                total -= semuaakundetil.kredit
            if round(total, 2) != 0:
                res[jurnalpenutup.id] = "Jurnal Tidak Balance"
        return res

    # Isi tanggal, secara otomatis akhir bulan
    def onchange_tanggal(self, cr, uid, ids, bulan, tahun, context=None):
        res = {}
        if bulan and tahun:
            tanggal = False
            if int(bulan) == 12:
                tanggal = datetime.date(int(tahun)+1, 1, 1)
            else:
                tanggal = datetime.date(int(tahun), int(bulan)+1, 1)
            res['tanggal'] = tanggal - datetime.timedelta(days=1)
        return {'value': res}

    _columns = {
        'bulan' : fields.selection([('01', 'Januari'), ('02', 'Februari'), ('03', 'Maret')
                                        , ('04', 'April'), ('05', 'Mei'), ('06', 'Juni'), ('07', 'Juli')
                                        , ('08', 'Agustus'), ('09', 'September'), ('10', 'Oktober'), ('11', 'November')
                                        , ('12', 'Desember')], "Bulan", required=True), 
        'tahun' : fields.selection([('2015', '2015'), ('2016', '2016'), ('2017', '2017')
                                        , ('2018', '2018'), ('2019', '2019'), ('2020', '2020'), ('2021', '2021')
                                        , ('2022', '2022'), ('2023', '2023'), ('2024', '2024'), ('2025', '2025')], "Tahun", required=True), 
        'tanggal' : fields.date("Tanggal Penutupan"), 
        'akunterkena': fields.one2many("mmr.akundetil", "sumberjurnalpenutup", "Jurnal"), 
        'status' : fields.function(_set_status, type="char", method=True, string="Status"), 
        'notes' : fields.text("Notes"), 
    }
    
    def create(self, cr, uid, vals, context=None):
        id = super(mmr_jurnalpenutup, self).create(cr, uid, vals, context)
        validasijurnalpenutup(self, cr, uid, id)
        return id
    
    def write(self, cr, uid, ids, vals, context=None):
        super(mmr_jurnalpenutup, self).write(cr, uid, ids, vals, context=context)
        validasijurnalpenutup(self, cr, uid, ids)
        return super(mmr_jurnalpenutup, self).write(cr, uid, ids, vals, context=context)
    
mmr_jurnalpenutup()

class mmr_akundummy(osv.osv):
    
    # Akun Dummy digunakan untuk laporan
    # Setiap kali akan melihat laporan buat akun dummy, seharusnya laporan tinggal mengambil dari akun yang ada
    # Ini akan memakan memory

    _name = "mmr.akundummy"
    _description = "Modul akun dummy untuk laporan PT. MMR."
    _rec_name = "namaakun"
    _order = "nomorakun"
    
    _columns = {
        'idakunparent' : fields.selection([('activa', '1. Activa'), ('hutang', '2. Hutang'), ('modal', '3. Modal')
                                        , ('penjualan', '4. Penjualan'), ('pembelian', '5. Pembelian'), ('biaya', '6. Biaya')
                                        , ('pendapatandiluarusaha', '7. Pendapatan di Luar Usaha'), ('bebandiluarusaha', '8. Beban di Luar Usaha')], "Golongan", required=True), 
        'nomorakun': fields.char("Nomor Akun", required=True), 
        'namaakun': fields.char("Nama Akun", required=True), 
        'debit': fields.float("Debit", digits=(12, 2)), 
        'kredit': fields.float("Kredit", digits=(12, 2)), 
        'akundetil': fields.one2many("mmr.akundetildummy", "idakun", "History"), 
        'normaldi' : fields.selection([('debit', 'Debit'), ('kredit', 'Kredit'), ('debitkredit', 'Debit Kredit')], "Normal Di", required=True), 
        'idjurnal' : fields.many2one("mmr.laporanjurnal", "IDJURNAL"), 
        'idjurnalpenyesuaian' : fields.many2one("mmr.laporanjurnal", "IDJURNALPENYESUAIAN"), 
        'idjurnaldisesuaikan' : fields.many2one("mmr.laporanjurnal", "IDJURNALDISESUAIKAN"), 
        'idjurnalpenutup' : fields.many2one("mmr.laporanjurnal", "IDJURNALPENUTUP"), 
    }    
    
mmr_akundummy()

class mmr_akundetildummy(osv.osv):
    _name = "mmr.akundetildummy"
    _description = "Modul akun dummy untuk laporan PT. MMR."
    
    _columns = {
        'idakun': fields.many2one("mmr.akundummy", "Nama Akun"), 
        'idcetakbackup' : fields.many2one("mmr.cetakbackup", "cetakbackup"), 
        'tanggal': fields.date("Waktu"), 
        'sumber' : fields.char("Sumber"), 
        'debit': fields.float("Debit", digits=(12, 2)), 
        'kredit': fields.float("Kredit", digits=(12, 2)), 
    }
    
mmr_akundetildummy()


class mmr_laporanjurnal(osv.osv):
    _name = "mmr.laporanjurnal"
    _description = "Modul Memory Laporan Jurnal untuk PT. MMR"
    _rec_name = "bulan"

    @api.one
    def simpan_akun(self):
        if self.bulan and self.tahun:
            tanggal = False
            if int(self.bulan) == 12:
                tanggal = datetime.date(int(self.tahun)+1, 1, 1)
            else:
                tanggal = datetime.date(int(self.tahun), int(self.bulan)+1, 1)
            tanggal = tanggal - datetime.timedelta(days=1)
            akundetil = []
            for akun in self.env['mmr.akun'].search([]):
                nilaidisesuaikandebit = 0
                nilaidisesuaikankredit = 0
                nilaipenutupdebit = 0
                nilaipenutupkredit = 0
                for akundisesuaikan in self.jurnaldisesuaikan:
                    if akun.nomorakun == akundisesuaikan.nomorakun:
                        nilaidisesuaikandebit = akundisesuaikan.debit
                        nilaidisesuaikankredit = akundisesuaikan.kredit
                for akunpenutup in self.jurnalpenutup:
                    if akun.nomorakun == akunpenutup.nomorakun:
                        nilaipenutupdebit = akunpenutup.debit
                        nilaipenutupkredit = akunpenutup.kredit
                if akun.normaldi == 'debit':
                    akundetil.append((0, 0, {'idakun': akun.id, 'debit': (nilaidisesuaikandebit - nilaidisesuaikankredit) + (nilaipenutupdebit - nilaipenutupkredit)}))
                elif akun.normaldi == 'kredit':
                    akundetil.append((0, 0, {'idakun': akun.id, 'kredit': (nilaidisesuaikankredit - nilaidisesuaikandebit) + (nilaipenutupkredit - nilaipenutupdebit)}))
            self.env['mmr.saveakun'].create({'tanggal': tanggal, 'idssaveakun': akundetil})

    @api.multi
    def ambil_tanggal(self):
        for semuaakun in self.env['mmr.akundetil'].search([]):
            if semuaakun.sumberpembelianfaktur:
                semuaakun.tanggal = semuaakun.sumberpembelianfaktur.tanggalterbit
            elif semuaakun.sumberpenjualanfaktur:
                semuaakun.tanggal = semuaakun.sumberpenjualanfaktur.tanggalterbit
            elif semuaakun.sumberpembayaranpembelian:
                semuaakun.tanggal = semuaakun.sumberpembayaranpembelian.tanggalbayar
            elif semuaakun.sumberpembayaranpenjualan:
                semuaakun.tanggal = semuaakun.sumberpembayaranpenjualan.tanggalbayar
            elif semuaakun.sumberkegiatanakunting:
                semuaakun.tanggal = semuaakun.sumberkegiatanakunting.tanggal
            elif semuaakun.sumberbiaya:
                semuaakun.tanggal = semuaakun.sumberbiaya.tanggal
            elif semuaakun.sumberinventaris:
                semuaakun.tanggal = semuaakun.sumberinventaris.tanggal
            elif semuaakun.sumberjurnalpenyesuaian:
                semuaakun.tanggal = semuaakun.sumberjurnalpenyesuaian.tanggal
            elif semuaakun.sumberjurnalpenutup:
                semuaakun.tanggal = semuaakun.sumberjurnalpenutup.tanggal
            elif semuaakun.sumberjurnalringkasan:
                tanggalperingkasan = "01" + semuaakun.sumberjurnalringkasan.bulan + semuaakun.sumberjurnalringkasan.tahun
                semuaakun.tanggal = datetime.datetime.strptime(tanggalperingkasan, "%d%m%Y").date()

    # Isi laporan jurnal sesuai dengan bulan yang dipilih
    # Tampilkan seluruh akun dan sumber nilai akun tsb ( Jurnal - jurnalnya )
    # Apabila akun 1 - 3 yang berlanjut ( Tidak ditutup ) Diringkas menjadi saldo awal
    @api.one
    @api.onchange('bulan', 'tahun')
    def _isi_jurnal(self):
        self.jurnal = False
        self.jurnalpenyesuaian = False
        self.jurnaldisesuaikan = False
        self.jurnalpenutup = False
        bulan = self.bulan
        tahun = self.tahun
        if bulan and tahun:
            # Hapus dulu semua record ini -1 hari, agar tidak memakan banyak space pada database
            hariminus1 = datetime.datetime.today() - datetime.timedelta(days=1)
            self.env['mmr.akundetildummy'].search([('create_date', '<', datetime.datetime.strftime(hariminus1, "%Y-%m-%d"))]).unlink()
            self.env['mmr.akundummy'].search([('create_date', '<', datetime.datetime.strftime(hariminus1, "%Y-%m-%d"))]).unlink()

            # Ambil seluruh akun yang ada, salin ulang pada jurnal
            # Nilai berlanjut ( Akun 1-3 ) Dijumlah dan diberi nama saldo awal
            saveakunterakhir = self.env['mmr.saveakun'].search([('tanggal', '<', datetime.date(int(tahun), int(bulan), 1))], limit=1, order='tanggal desc')
            hasilsearch = self.env['mmr.akun'].search([])

            for semuahasilsearch in hasilsearch:
                akundetil = self.env['mmr.akundetildummy']
                akundetilpenyesuaian = self.env['mmr.akundetildummy']
                akundetildisesuaikan = self.env['mmr.akundetildummy']
                akundetilpenutup = self.env['mmr.akundetildummy']
                nilaidebit = False
                nilaikredit = False
                nilaipenyesuaiandebit = False
                nilaipenyesuaiankredit = False
                nilaidisesuaikandebit = False
                nilaidisesuaikankredit = False
                nilaipenutupdebit = False
                nilaipenutupkredit = False
                saldoawal = 0

                listakundetilid = []
                if saveakunterakhir:
                    if semuahasilsearch.normaldi == 'debit':
                        saldoawal = round((self.env['mmr.saveakundetil'].search([('idsaveakun', '=', saveakunterakhir.id), ('idakun', '=', semuahasilsearch.id)], limit=1).debit - self.env['mmr.saveakundetil'].search([('idsaveakun', '=', saveakunterakhir.id), ('idakun', '=', semuahasilsearch.id)], limit=1).kredit), 2)
                    elif semuahasilsearch.normaldi == 'kredit':
                        saldoawal = round((self.env['mmr.saveakundetil'].search([('idsaveakun', '=', saveakunterakhir.id), ('idakun', '=', semuahasilsearch.id)], limit=1).kredit - self.env['mmr.saveakundetil'].search([('idsaveakun', '=', saveakunterakhir.id), ('idakun', '=', semuahasilsearch.id)], limit=1).debit), 2)
                    self.env.cr.execute('SELECT id FROM mmr_akundetil where tanggal>%s and idakun=%s', [saveakunterakhir.tanggal, semuahasilsearch.id])
                    listakundetil = self.env.cr.fetchall()
                    for eachlistakundetil in listakundetil:
                        listakundetilid.append(eachlistakundetil[0])
                else:
                    self.env.cr.execute('SELECT id FROM mmr_akundetil where idakun=%s', [semuahasilsearch.id])
                    listakundetil = self.env.cr.fetchall()
                    for eachlistakundetil in listakundetil:
                        listakundetilid.append(eachlistakundetil[0])

                if semuahasilsearch.normaldi == 'debit':
                    nilaidebit += saldoawal
                    nilaidisesuaikandebit += saldoawal
                else:
                    nilaikredit += saldoawal
                    nilaidisesuaikankredit += saldoawal

                # for semuaakundetil in semuahasilsearch.akundetil:
                for semuaakundetil in self.env['mmr.akundetil'].browse(listakundetilid):
                    tanggal, sumber = False, False
                    if semuaakundetil.sumberpembelianfaktur:
                        tanggal = semuaakundetil.sumberpembelianfaktur.tanggalterbit
                        sumber = "Faktur Nomor : " + str(semuaakundetil.sumberpembelianfaktur.nomorfaktur)
                    elif semuaakundetil.sumberpenjualanfaktur:
                        tanggal = semuaakundetil.sumberpenjualanfaktur.tanggalterbit
                        sumber = "Faktur Nomor : " + str(semuaakundetil.sumberpenjualanfaktur.nomorfaktur)
                    elif semuaakundetil.sumberpembayaranpembelian:
                        tanggal = semuaakundetil.sumberpembayaranpembelian.tanggalbayar
                        sumber = "Pembayaran Pembelian Untuk : " + str(semuaakundetil.sumberpembayaranpembelian.supplier.nama)
                    elif semuaakundetil.sumberpembayaranpenjualan:
                        tanggal = semuaakundetil.sumberpembayaranpenjualan.tanggalbayar
                        sumber = "Pembayaran Pembelian Untuk : " + str(semuaakundetil.sumberpembayaranpenjualan.customer.nama)
                    elif semuaakundetil.sumberkegiatanakunting:
                        tanggal = semuaakundetil.sumberkegiatanakunting.tanggal
                        sumber = "Kegiatan Akunting : " + str(semuaakundetil.sumberkegiatanakunting.detilkejadian)
                    elif semuaakundetil.sumberbiaya:
                        tanggal = semuaakundetil.sumberbiaya.tanggal
                        sumber = "Biaya : " + str(semuaakundetil.sumberbiaya.detilkejadian)
                    elif semuaakundetil.sumberinventaris:
                        tanggal = semuaakundetil.sumberinventaris.tanggal
                        sumber = "Inventaris : " + str(semuaakundetil.sumberinventaris.nama)
                    elif semuaakundetil.sumberjurnalpenyesuaian:
                        tanggal = semuaakundetil.sumberjurnalpenyesuaian.tanggal
                        sumber = "Jurnal Penyesuaian : " + str(semuaakundetil.sumberjurnalpenyesuaian.tanggal)
                    elif semuaakundetil.sumberjurnalpenutup:
                        tanggal = semuaakundetil.sumberjurnalpenutup.tanggal
                        sumber = "Jurnal Penutup : " + str(semuaakundetil.sumberjurnalpenutup.tanggal)
                    elif semuaakundetil.sumberjurnalringkasan:
                        tanggalperingkasan = "01" + semuaakundetil.sumberjurnalringkasan.bulan + semuaakundetil.sumberjurnalringkasan.tahun
                        tanggal = str(datetime.datetime.strptime(tanggalperingkasan, "%d%m%Y"))
                        sumber = "Jurnal Peringkas : bulan: " + str(semuaakundetil.sumberjurnalringkasan.bulan) + ", tahun: " + str(semuaakundetil.sumberjurnalringkasan.tahun)

                    # Deprecated, tanggal pada pembayaran sudah required!
                    if not tanggal:
                        raise osv.except_osv(_('Tidak Dapat Melanjutkan'), _("Ada jurnal pembayaran yang belum disetujui"))

                    self.env.cr.execute('SELECT debit FROM mmr_akundetil where id=%s', [semuaakundetil.id])
                    semuaakundetildebit = round(self.env.cr.fetchone()[0], 2)
                    self.env.cr.execute('SELECT kredit FROM mmr_akundetil where id=%s', [semuaakundetil.id])
                    semuaakundetilkredit = round(self.env.cr.fetchone()[0], 2)

                    if tahun == tanggal[0:4] and bulan == tanggal[5:7]:
                        if semuaakundetil.sumberjurnalpenyesuaian:
                            akundetilpenyesuaian += self.env['mmr.akundetildummy'].new({'debit': semuaakundetildebit, 'kredit': semuaakundetilkredit, 'sumber': sumber, 'tanggal': tanggal})
                            akundetildisesuaikan += self.env['mmr.akundetildummy'].new({'debit': semuaakundetildebit, 'kredit': semuaakundetilkredit, 'sumber': sumber, 'tanggal': tanggal})
                            nilaidisesuaikandebit += semuaakundetildebit
                            nilaidisesuaikankredit += semuaakundetilkredit
                            nilaipenyesuaiandebit += semuaakundetildebit
                            nilaipenyesuaiankredit += semuaakundetilkredit
                        elif semuaakundetil.sumberjurnalpenutup:
                            akundetilpenutup += self.env['mmr.akundetildummy'].new({'debit': semuaakundetildebit, 'kredit': semuaakundetilkredit, 'sumber': sumber, 'tanggal': tanggal})
                            nilaipenutupdebit += semuaakundetildebit
                            nilaipenutupkredit += semuaakundetilkredit
                        else:
                            akundetil += self.env['mmr.akundetildummy'].new({'debit': semuaakundetildebit, 'kredit': semuaakundetilkredit, 'sumber': sumber, 'tanggal': tanggal})
                            akundetildisesuaikan += self.env['mmr.akundetildummy'].new({'debit': semuaakundetildebit, 'kredit': semuaakundetilkredit, 'sumber': sumber, 'tanggal': tanggal})
                            nilaidebit += semuaakundetildebit
                            nilaikredit += semuaakundetilkredit
                            nilaidisesuaikandebit += semuaakundetildebit
                            nilaidisesuaikankredit += semuaakundetilkredit
                    elif tahun + bulan > tanggal[0:4] + tanggal[5:7]:
                        if semuahasilsearch.normaldi == 'debit':
                            saldoawal += semuaakundetildebit
                            saldoawal -= semuaakundetilkredit
                        else:
                            saldoawal -= semuaakundetildebit
                            saldoawal += semuaakundetilkredit

                        nilaidebit += semuaakundetildebit
                        nilaikredit += semuaakundetilkredit
                        nilaidisesuaikandebit += semuaakundetildebit
                        nilaidisesuaikankredit += semuaakundetilkredit

                if saldoawal != 0:
                    tanggal = datetime.date(int(tahun), int(bulan), 1)
                    if semuahasilsearch.normaldi == 'debit':
                        akundetil += self.env['mmr.akundetildummy'].new({'debit': saldoawal, 'kredit': 0,
                                                                'sumber': 'Saldo Awal', 'tanggal': tanggal})
                        akundetildisesuaikan += self.env['mmr.akundetildummy'].new({'debit': saldoawal, 'kredit': 0, 'sumber': 'Saldo Awal', 'tanggal': tanggal})
                    else:
                        akundetil += self.env['mmr.akundetildummy'].new({'debit': 0, 'kredit': saldoawal, 'sumber': 'Saldo Awal', 'tanggal': tanggal})
                        akundetildisesuaikan += self.env['mmr.akundetildummy'].new({'debit': saldoawal, 'kredit': 0, 'sumber': 'Saldo Awal', 'tanggal': tanggal})
                if semuahasilsearch.normaldi == 'debit':
                    if nilaidebit - nilaikredit >= 0:
                        self.jurnal += self.jurnal.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': round((nilaidebit-nilaikredit), 2), 'kredit': 0, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetil})
                    else:
                        self.jurnal += self.jurnal.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': 0, 'kredit': round(-1*(nilaidebit-nilaikredit), 2), 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetil})
                    if nilaipenyesuaiandebit - nilaipenyesuaiankredit >= 0:
                        self.jurnalpenyesuaian += self.jurnalpenyesuaian.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': round((nilaipenyesuaiandebit - nilaipenyesuaiankredit), 2), 'kredit': 0, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenyesuaian})
                    else:
                        self.jurnalpenyesuaian += self.jurnalpenyesuaian.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': 0, 'kredit': round(-1*(nilaipenyesuaiandebit - nilaipenyesuaiankredit), 2), 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenyesuaian})
                    if nilaidisesuaikandebit - nilaidisesuaikankredit >= 0:
                        self.jurnaldisesuaikan += self.jurnaldisesuaikan.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': round((nilaidisesuaikandebit - nilaidisesuaikankredit), 2), 'kredit': 0, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetildisesuaikan})
                    else:
                        self.jurnaldisesuaikan += self.jurnaldisesuaikan.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': 0, 'kredit': round(-1*(nilaidisesuaikandebit - nilaidisesuaikankredit), 2), 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetildisesuaikan})
                    if nilaipenutupdebit - nilaipenutupkredit >= 0:
                        self.jurnalpenutup += self.jurnalpenutup.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': round((nilaipenutupdebit - nilaipenutupkredit), 2), 'kredit': 0, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenutup})
                    else:
                        self.jurnalpenutup += self.jurnalpenutup.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': 0, 'kredit': round(-1*(nilaipenutupdebit - nilaipenutupkredit), 2), 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenutup})
                elif semuahasilsearch.normaldi == 'kredit':
                    if nilaikredit - nilaidebit >= 0:
                        self.jurnal += self.jurnal.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': 0, 'kredit': round((nilaikredit - nilaidebit), 2), 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetil})
                    else:
                        self.jurnal += self.jurnal.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': round(-1*(nilaikredit - nilaidebit), 2), 'kredit': 0, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetil})
                    if nilaipenyesuaiankredit - nilaipenyesuaiandebit >= 0:
                        self.jurnalpenyesuaian += self.jurnalpenyesuaian.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun,  'namaakun': semuahasilsearch.namaakun, 'debit': 0, 'kredit': round((nilaipenyesuaiankredit - nilaipenyesuaiandebit), 2), 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenyesuaian})
                    else:
                        self.jurnalpenyesuaian += self.jurnalpenyesuaian.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': round(-1*(nilaipenyesuaiankredit - nilaipenyesuaiandebit), 2), 'kredit': 0, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenyesuaian})
                    if nilaidisesuaikankredit - nilaidisesuaikandebit >= 0:
                        self.jurnaldisesuaikan += self.jurnaldisesuaikan.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': 0, 'kredit': round((nilaidisesuaikankredit - nilaidisesuaikandebit), 2), 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetildisesuaikan})
                    else:
                        self.jurnaldisesuaikan += self.jurnaldisesuaikan.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': round(-1*(nilaidisesuaikankredit - nilaidisesuaikandebit), 2), 'kredit': 0, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetildisesuaikan})
                    if nilaipenutupkredit - nilaipenutupdebit >= 0:
                        self.jurnalpenutup += self.jurnalpenutup.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': 0, 'kredit': round((nilaipenutupkredit - nilaipenutupdebit), 2), 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenutup})
                    else:
                        self.jurnalpenutup += self.jurnalpenutup.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': round(-1*(nilaipenutupkredit - nilaipenutupdebit), 2), 'kredit': 0, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenutup})
                else:
                    self.jurnal += self.jurnal.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': nilaidebit, 'kredit': nilaikredit, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetil})
                    self.jurnalpenyesuaian += self.jurnalpenyesuaian.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': nilaipenyesuaiandebit, 'kredit':  nilaipenyesuaiankredit, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenyesuaian})
                    self.jurnaldisesuaikan += self.jurnaldisesuaikan.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': nilaidisesuaikandebit, 'kredit': nilaidisesuaikankredit, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetildisesuaikan})
                    self.jurnalpenutup += self.jurnalpenutup.new({'idakunparent': semuahasilsearch.idakunparent, 'nomorakun': semuahasilsearch.nomorakun, 'namaakun': semuahasilsearch.namaakun, 'debit': nilaipenutupdebit, 'kredit': nilaipenutupkredit, 'normaldi': semuahasilsearch.normaldi, 'akundetil': akundetilpenutup})

    # Isi nilai debit dan kredit jurnal penutup/penyesuaian/neraca lajur
    @api.one
    @api.depends("jurnalpenutup")    
    def _isi_debitkreditjurnalpenutup(self):
        self.jurnalpenutupdebit, self.jurnalpenutupkredit = False, False
        if self.jurnalpenutup:
            for semuajurnalpenutupdetil in self.jurnalpenutup:
                self.jurnalpenutupdebit += semuajurnalpenutupdetil.debit            
                self.jurnalpenutupkredit += semuajurnalpenutupdetil.kredit    
    
    @api.one
    @api.depends("jurnal")    
    def _isi_debitkreditjurnal(self):
        self.jurnaldebit, self.jurnalkredit = False, False
        if self.jurnal:
            for semuajurnaldetil in self.jurnal:
                self.jurnaldebit += semuajurnaldetil.debit            
                self.jurnalkredit += semuajurnaldetil.kredit    
                
    @api.one
    @api.depends("jurnalpenyesuaian")    
    def _isi_debitkreditjurnalpenyesuaian(self):
        self.jurnalpenyesuaiandebit, self.jurnalpenyesuaiankredit = False, False
        if self.jurnalpenyesuaian:
            for semuajurnalpenyesuaiandetil in self.jurnalpenyesuaian:
                self.jurnalpenyesuaiandebit += semuajurnalpenyesuaiandetil.debit            
                self.jurnalpenyesuaiankredit += semuajurnalpenyesuaiandetil.kredit    
    
    @api.one
    @api.depends("jurnaldisesuaikan")    
    def _isi_debitkreditjurnaldisesuaikan(self):
        self.jurnaldisesuaikandebit, self.jurnaldisesuaikankredit = False, False
        if self.jurnaldisesuaikan:
            for semuajurnaldisesuaikandetil in self.jurnaldisesuaikan:
                self.jurnaldisesuaikandebit += semuajurnaldisesuaikandetil.debit            
                self.jurnaldisesuaikankredit += semuajurnaldisesuaikandetil.kredit    
                                    
    _columns = {
            'modellaporan' : fields.selection([('neraca', 'Neraca') , ('labarugi', 'Laba/Rugi'), ('neracalajur', 'Neraca Lajur'), ('jurnalpenyesuaian', 'Jurnal Penyesuaian'), ('neracadisesuaikan', 'Neraca Disesuaikan')
                                        , ('jurnalpenutup', 'Jurnal Penutup'), ('bukubesar', 'Buku Besar')], "Jenis Laporan", required=True), 
            'bulan' : fields.selection([('01', 'Januari'), ('02', 'Februari'), ('03', 'Maret')
                                        , ('04', 'April'), ('05', 'Mei'), ('06', 'Juni'), ('07', 'Juli')
                                        , ('08', 'Agustus'), ('09', 'September'), ('10', 'Oktober'), ('11', 'November')
                                        , ('12', 'Desember')], "Bulan", required=True), 
            'tahun' : fields.selection([('2015', '2015'), ('2016', '2016'), ('2017', '2017')
                                        , ('2018', '2018'), ('2019', '2019'), ('2020', '2020'), ('2021', '2021')
                                        , ('2022', '2022'), ('2023', '2023'), ('2024', '2024'), ('2025', '2025')], "Tahun", required=True), 
            'jurnal' : fields.one2many("mmr.akundummy", "idjurnal", "Laporan Jurnal"), 
            'jurnaldebit' : fields.float("Debit", compute=_isi_debitkreditjurnal, store=True, digits=(12, 2)), 
            'jurnalkredit' : fields.float("Kredit", compute=_isi_debitkreditjurnal, store=True, digits=(12, 2)), 
            'jurnalpenyesuaian' : fields.one2many("mmr.akundummy", "idjurnalpenyesuaian", "Laporan Jurnal Penyesuaian"), 
            'jurnalpenyesuaiandebit' : fields.float("Debit", compute=_isi_debitkreditjurnalpenyesuaian, store=True, digits=(12, 2)), 
            'jurnalpenyesuaiankredit' : fields.float("Kredit", compute=_isi_debitkreditjurnalpenyesuaian, store=True, digits=(12, 2)), 
            'jurnaldisesuaikan' : fields.one2many("mmr.akundummy", "idjurnaldisesuaikan", "Laporan Jurnal Disesuaikan"), 
            'jurnaldisesuaikandebit' : fields.float("Debit", compute=_isi_debitkreditjurnaldisesuaikan, store=True, digits=(12, 2)), 
            'jurnaldisesuaikankredit' : fields.float("Kredit", compute=_isi_debitkreditjurnaldisesuaikan, store=True, digits=(12, 2)), 
            'jurnalpenutup' : fields.one2many("mmr.akundummy", "idjurnalpenutup", "Laporan Jurnal Penutup"), 
            'jurnalpenutupdebit' : fields.float("Debit", compute=_isi_debitkreditjurnalpenutup, store=True, digits=(12, 2)), 
            'jurnalpenutupkredit' : fields.float("Kredit", compute=_isi_debitkreditjurnalpenutup, store=True, digits=(12, 2)), 
            'trigger' : fields.char("Trigger", compute=_isi_jurnal ), 
            }
    
mmr_laporanjurnal()


class mmr_aturanakun(osv.osv):
    
    # Aturan akuntansi, template jurnal agar penjurnalan tidak perlu dilakukan manual
    
    _name = "mmr.aturanakun"
    _description = "Modul aturan akun untuk PT. MMR."
    _rec_name = "namaaturan"
    
    _columns = {
        'namaaturan' : fields.char("Nama Aturan", required=True), 
        'model': fields.many2one("ir.model", "Model", domain="[('model', 'like', 'mmr.')]", required=True), 
        'aturanakundetil' : fields.one2many("mmr.aturanakundetil", "idaturanakun", "Fields"), 
        'notes' : fields.text("Notes"), 
    }    
    
    # Apabila ada perubahan aturan, ikut ubah seluruh jurnal yang menggunakan aturan ini
    def write(self, cr, uid, id, vals, context=None):
        res = super(mmr_aturanakun, self).write(cr, uid, id, vals, context)
        objini = self.browse(cr, uid, id)
        modelClass = self.pool.get(objini.model.model)
        akunClass = self.pool.get("mmr.akundetil")
        hasilsearch = modelClass.search(cr, uid, [("aturanakun", "=", objini.id)])
        
        for semuahasilsearch in hasilsearch:
            modelobj = modelClass.browse(cr, uid, semuahasilsearch)
            modelobj.akunterkena.unlink()
            for semuaakundetil in objini.aturanakundetil:
                if objini.model.model == "mmr.pembelianfaktur":
                    akunClass.create(cr, uid, {"idakun":semuaakundetil.noakun.id, "sumberpembelianfaktur": semuahasilsearch, "tanggal":modelobj.write_date})
                elif objini.model.model == "mmr.penjualanfaktur":
                    akunClass.create(cr, uid, {"idakun":semuaakundetil.noakun.id, "sumberpenjualanfaktur": semuahasilsearch, "tanggal":modelobj.write_date})
                elif objini.model.model == "mmr.pembayaranpembelian":
                    akunClass.create(cr, uid, {"idakun":semuaakundetil.noakun.id, "sumberpembayaranpembelian": semuahasilsearch, "tanggal":modelobj.write_date})
                elif objini.model.model == "mmr.pembayaranpenjualan":
                    akunClass.create(cr, uid, {"idakun":semuaakundetil.noakun.id, "sumberpembayaranpenjualan": semuahasilsearch, "tanggal":modelobj.write_date})
                elif objini.model.model == "mmr.biaya":
                    akunClass.create(cr, uid, {"idakun":semuaakundetil.noakun.id, "sumberbiaya": semuahasilsearch, "tanggal":modelobj.write_date})

        return res
        
mmr_aturanakun()

class mmr_aturanakundetil(osv.osv):
    _name = "mmr.aturanakundetil"
    _description = "Modul aturan akun detil untuk PT. MMR."
    
    _columns = {
        'idaturanakun' : fields.many2one("mmr.aturanakun", ondelete='cascade'), 
        'model': fields.many2one("ir.model", "Model", related="idaturanakun.model", required=True), 
        'field': fields.many2one("ir.model.fields", domain="[('model_id', '=', model), ('ttype', '=', 'float')]", string="Fields" , required=True), 
        'noakun' : fields.many2one("mmr.akun", "Nama Akun", required=True), 
        'debitkredit' : fields.selection([('debit', 'Debit'), ('kredit', 'Kredit')], "Debit / Kredit", required=True), 
    }    
        
mmr_aturanakundetil()

class mmr_kegiatanakunting(osv.osv):
    
    # Wadah Pencatatn jurnal kegiatan akunting ( Alias Jurnal lain- lain )
    
    _name = "mmr.kegiatanakunting"
    _description = "Modul kegiatan akunting untuk PT. MMR."
    
        # Setujui Faktur, sekali disetujui tidak dapat diedit
    # Begitu faktur disetujui, SJ yang difaktur Ikut dikunci.
    def setuju(self, cr, uid, ids, context):
        userclass = self.pool.get("res.users")
        userobj = userclass.browse(cr, uid, uid)
        self.write(cr, uid, ids, {'disetujui':userobj.login})
    
    def revisi(self, cr, uid, ids, context):
        self.write(cr, uid, ids, {'disetujui':False})
        
    def _set_status(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        res = {}
        for kegiatanakunting in self.browse(cr, uid, ids):
            res[kegiatanakunting.id] = "Normal"
            total = 0    
            for semuaakundetil in kegiatanakunting.akunterkena:
                total+=semuaakundetil.debit
                total-=semuaakundetil.kredit
            if round(total, 2)!=0:
                res[kegiatanakunting.id] = "Jurnal Tidak Balance"
                
        return res
    
    _columns = {
        'tanggal' : fields.date("Tanggal Kejadian", required=True), 
        'detilkejadian' : fields.char("Detil Kejadian", required=True), 
        'status' : fields.function(_set_status, type="char", method=True, string="Status"), 
        "akunterkena" : fields.one2many("mmr.akundetil", "sumberkegiatanakunting", "Jurnal"), 
        'disetujui' : fields.char("Disetujui"), 
        'notes' : fields.text("Notes"), 
    }    
    
    # Jangan dapat dihapus apabila PO telah disetujui admin dan ( sales / kepala sales )
    def unlink(self, cr, uid, ids, context):
        ids = [ids]
        for id in ids:
            kegiatanakuntingobj = self.browse(cr, uid, id)
            if kegiatanakuntingobj.disetujui != False and 'ijindelete' not in context:
                raise osv.except_osv(_('Tidak Dapat Menghapus'), _("Kegiatan Akunting Telah Disetujui!"))
            super(mmr_kegiatanakunting, self).unlink(cr, uid, id, context)
        return True
    
    # Jangan dapat dicopy
    def copy(self, cr, uid, id, default=None, context=None):
           raise osv.except_osv(_('Tidak Dapat Duplikasi'), _('Dilarang melakukan duplikasi data Kegiatan Akunting.'))
           return True
        
mmr_kegiatanakunting()

class mmr_biaya(osv.osv):
    
    # Wadah Pencatatn jurnal biaya
    
    _name = "mmr.biaya"
    _description = "Modul biaya untuk PT. MMR."
    
    def setuju(self, cr, uid, ids, context):
        if self.browse(cr, uid, ids).aturanakun or not self.browse(cr, uid, ids).akunotomatis:
            userclass = self.pool.get("res.users")
            userobj = userclass.browse(cr, uid, uid)
            self.write(cr, uid, ids, {'disetujui':userobj.login})
        else:
            raise osv.except_osv(_('Tidak Dapat Melanjutkan'), _("Isi Jurnal dahulu."))    
    
    def revisi(self, cr, uid, ids, context):
        self.write(cr, uid, ids, {'disetujui':False})
    
    # Jangan bisa diubah apabila bukan otoritas / pembuat
    def onchange_jumlahbiaya(self, cr, uid, ids, context=None):
        res = {}
        if ids:
            grupClass = self.pool.get("res.groups")
            grupobj = grupClass.search(cr, uid, [('name', '=', 'Otoritas')])
            userClass = self.pool.get("res.users")
            grupditemukan = False
            for semuagrup in userClass.browse(cr, uid, uid).groups_id:
                if semuagrup.id == grupobj[0]:
                    grupditemukan = True
            if self.browse(cr, uid, ids).create_uid.id != uid and not grupditemukan:
                res['jumlahbiaya'] = self.browse(cr, uid, ids).jumlahbiaya
                    
        return {'value': res}
        
    def _set_status(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        # SET STATUS---------------------------------
        res = {}
    
        for biaya in self.browse(cr, uid, ids):
            res[biaya.id]    = "Normal"
            
            total = 0    
            for semuaakundetil in biaya.akunterkena:
                total+=semuaakundetil.debit
                total-=semuaakundetil.kredit
                    
            if round(total, 2)!=0:
                res[biaya.id]    = "Jurnal Tidak Balance"
        return res
    
    def _ijin_kasir(self, cr, uid, ids, field_name, field_value, args=None, context=None):
        # SET STATUS---------------------------------
        res = {}
        for biaya in self.browse(cr, uid, ids):
            res[biaya.id]    = True
            
            total = 0    
            for semuaakundetil in biaya.akunterkena:
                if semuaakundetil.idakun.nomorakun == "1.1.02" or semuaakundetil.idakun.nomorakun == "1.1.03.1" or semuaakundetil.idakun.nomorakun == "1.1.03.2" or semuaakundetil.idakun.nomorakun == "1.1.07" or semuaakundetil.idakun.nomorakun == "1.1.09":
                    res[biaya.id]    = False
        return res
    
    #Isi jurnal secara otomatis berdasarkan aturan yang dipilih
    @api.one
    @api.onchange("jumlahbiaya", "aturanakun", "akunotomatis")
    def _isi_akun(self):
        if self.jumlahbiaya!=False and self.aturanakun!=False and self.akunotomatis != False:
            data= {'jumlahbiaya':self.jumlahbiaya}
            self.akunterkena = False
            
            for semuaakundetil in self.aturanakun.aturanakundetil:
                if semuaakundetil.debitkredit =="debit":
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id, "tanggal":self.tanggal, "kredit": 0, 
                                                                "debit": data[semuaakundetil.field.name], "sumberbiaya": self.id, "notes": False})
                else:
                    if data[semuaakundetil.field.name] != 0:
                        self.akunterkena+=self.env['mmr.akundetil'].new({"idakun":semuaakundetil.noakun.id, "tanggal":self.tanggal, "kredit": 0, 
                                                                "kredit": data[semuaakundetil.field.name], "sumberbiaya": self.id, "notes": False})
        return self
    
    _columns = {
        'tanggal' : fields.date("Tanggal Kejadian", required=True), 
        'detilkejadian' : fields.char("Detil Kejadian", required=True), 
        'jumlahbiaya' : fields.float("Total Biaya", required=True, digits=(12, 2)), 
        'status' : fields.function(_set_status, type="char", method=True, string="Status"), 
        "aturanakun" : fields.many2one("mmr.aturanakun", "Aturan Jurnal", domain="[('model', '=', namamodel)]"), 
        'akunotomatis': fields.boolean("Otomatisasi Jurnal", help="Apabila tercentang, jurnal akan diisi otomatis sesuai data yang ada! Sebaliknya, jurnal tidak akan diisi otomatis dan user dapat mengubah jurnal secara manual!"), 
        "akunterkena" : fields.one2many("mmr.akundetil", "sumberbiaya", "Jurnal"), 
        'disetujui' : fields.char("Disetujui"), 
        'notes' : fields.text("Notes"), 
        'namamodel' : fields.char("NamaModel"), 
        'trigger' : fields.char("trigger", compute="_isi_akun"), 
    }    
    
    _defaults = {
                'namamodel' : "mmr.biaya", 
                'akunotomatis' : True, 
                }
    
    # Jangan dapat dihapus apabila PO telah disetujui admin dan ( sales / kepala sales )
    def unlink(self, cr, uid, ids, context):
        ids = [ids]
        for id in ids:
            biayaobj = self.browse(cr, uid, id)
            if biayaobj.disetujui != False and 'ijindelete' not in context:
                raise osv.except_osv(_('Tidak Dapat Menghapus'), _("Biaya Telah Disetujui!"))
            super(mmr_biaya, self).unlink(cr, uid, id, context)
        return True
    
    # Jangan dapat dicopy
    def copy(self, cr, uid, id, default=None, context=None):
           raise osv.except_osv(_('Tidak Dapat Duplikasi'), _('Dilarang melakukan duplikasi data Biaya.'))
           return True    
mmr_biaya()

def validasijurnalpenyesuaian(self, cr, uid, id, context=None):
    
    # Jangan ada jurnal penyesuaian untuk bulan dan tahun yang sama
    
    objini = self.browse(cr, uid, id)
    sqlQuery = """
    SELECT ID
    FROM mmr_jurnalpenyesuaian
    WHERE date_part('year', tanggal) = %s AND date_part('month', tanggal) = %s
    """% (objini.tanggal[0:4], objini.tanggal[5:7])
    cr.execute(sqlQuery)
    hasilquery = cr.dictfetchall()
    
    if len(hasilquery) > 1:
        raise osv.except_osv(_('Tidak Dapat Melanjutkan'), _("Sudah Ada Jurnal Penyesuaian Bulan dan Tahun Ini."))    

    return True

def validasijurnalpenutup(self, cr, uid, id, context=None):
    
    # Jangan ada jurnal penyesuaian untuk bulan dan tahun yang sama
        
    objini = self.browse(cr, uid, id)
    sqlQuery = """
    SELECT ID
    FROM mmr_jurnalpenutup
    WHERE date_part('year', tanggal) = %s AND date_part('month', tanggal) = %s
    """% (objini.tanggal[0:4], objini.tanggal[5:7])
    cr.execute(sqlQuery)
    hasilquery = cr.dictfetchall()
    
    if len(hasilquery) > 1:
        raise osv.except_osv(_('Tidak Dapat Melanjutkan'), _("Sudah Ada Jurnal Penutup Bulan dan Tahun Ini."))    

    return True
    