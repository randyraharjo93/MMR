{
  'name': 'MMR',
  'category': 'System',
  'version': '7.0.1.0',
  'description':
      """
      """,
	'author': 'Randy Raharjo',
	'maintainer': 'Randy Raharjo',
  'depends': ['base','web'], 
  'installable': True,
  'auto_install': False,
  'update_xml': [  
       'report_mmr.xml',           
       'report/popembelianreport.xml',  
       'report/popembelianreporttanpaharga.xml',   
       'report/sjpenjualanreport.xml', 
       'report/fakturpenjualanreport.xml',   
       'report/laporanlrreport.xml',     
       'report/laporanneracareport.xml',         
       'report/laporanneracalajurreport.xml',      
       'report/laporanneracalajurpenyesuaianreport.xml',   
       'report/laporanneracalajurdisesuaikanreport.xml',   
       'report/laporanneracalajurpenutupreport.xml',  
       'report/laporanbukubesarreport.xml',    
       'report/cetakbackupreport.xml',    
       'view/produk.xml',
       'view/supplier.xml',
       'view/pembelian.xml',
       'view/pembayaran.xml',
       'view/customer.xml',
       'view/sales.xml',
       'view/penjualan.xml',
       'view/groups.xml',
       'view/stok.xml',
       'view/akun.xml',
       'view/smart.xml',
       'cron/cronjob.xml',
       'menu/menu_master.xml',           
	],

  'js' : [
  ],
  'css' : [
  ],
  'qweb' : [
  ],
  'test': [
  ],
}
