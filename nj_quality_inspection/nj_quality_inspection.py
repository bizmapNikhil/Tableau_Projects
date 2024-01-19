import frappe
import json
# import cv2
# from erpnext.stock.doctype.quality_inspection.quality_inspection import  QualityInspection
# from nj_p1_features.nj_p1_features.doctype.machine_part_changes.machine_part_changes import get_basic_rate_for_remove_component,get_attribute_value_from_item, get_basic_rate_from_serial_no
from nj_p1_features.nj_p1_features.doctype.machine_part_changes.machine_part_changes import get_basic_rate_for_remove_component,get_attribute_value_from_item, get_actual_value, get_correct_basic_rate
from frappe.model.document import Document

class NJQualityInspection(Document):
    
    
    def on_submit(self):
        if self.status == 'In Progress':
            frappe.throw("NJ Quality Inspection cannot be submitted when Qi Status is 'In Progress'")
        self.check_manadatory_option()
        self.stock_entry()
        self.update_serial_no()
        self.get_nj_quality_readings_item_price()
        self.make_stock_entry()

    
    # stock entry for main item
    def make_stock_entry(self):
        new_jaisa_config=frappe.get_doc('NewJaisa Configuration')
        stock_entry = frappe.new_doc('Stock Entry')
        if self.inspection_type==new_jaisa_config.default_inspection_type:
           stock_entry.naming_series='SIQC-'
        else:
          stock_entry.naming_series='SEQC-'
        stock_entry.stock_entry_type = 'Repack'
        stock_entry.reference_type = 'NJ Quality Inspection'
        stock_entry.reference = self.name
        stock_entry.reference_serial_no = self.barcode
        stock_entry.company = frappe.db.get_single_value("Global Defaults", "default_company")
        warehouse = self.get_warehouse(serial_no=self.barcode)

        # NewJaisa configuration Data
        nj_conf = frappe.get_cached_doc("NewJaisa Configuration")

        # Source Warehouse
        purchase_rate = frappe.db.get_value('Serial No', self.barcode, 'purchase_rate') or 0.0
        stock_entry.append("items", {
            'barcode': self.barcode,
            'serial_no': self.barcode,
            'item_code': self.item_code,
            'item_group': self.item_group,
            'basic_rate':purchase_rate,
            'basic_amount':purchase_rate,
            'qty': 1,
            'uom': 'Nos',
            'conversion_factor': 1,
            'stock_uom': 'Nos',
            'expense_account': nj_conf.default_purchase_account if nj_conf.default_inspection_type == self.inspection_type else nj_conf.default_operational_cost_account,
            's_warehouse': warehouse,
            'is_finished_item': 0,
            'set_basic_rate_manually': True
        })

        # Target Warehouse
        if nj_conf.default_inspection_type == self.inspection_type:
            price_field = "preferred_purchase_price_"
        else:
            price_field = "current_price"
        
        item_price =  frappe.db.get_value('Serial No', self.barcode, price_field) or 0
        basic_rate = purchase_rate - item_price

        basic_rate = item_price
        print('********************',basic_rate)

        # stock_entry.total_incoming_value = item_price
        # if basic_rate < 0:
        #     basic_rate = abs(basic_rate)
        stock_entry.append("items", {
            'barcode': self.barcode,
            'serial_no': self.barcode,
            'item_code': self.item_code,
            'item_group': self.item_group,
            'basic_rate':basic_rate,
            "basic_amount": basic_rate,
            'qty': 1,
            'uom': 'Nos',
            'conversion_factor': 1,
            'stock_uom': 'Nos',
            'expense_account': nj_conf.default_purchase_account if nj_conf.default_inspection_type == self.inspection_type else nj_conf.default_operational_cost_account,
            't_warehouse': warehouse,
            'is_finished_item': 1,
            'set_basic_rate_manually': True
        })
        if getattr(stock_entry, "items", False): # only create if row is added
            stock_entry.save()
            stock_entry.submit()

    def stock_entry_items_object(self, stock_entry, index, s_warehouse, t_warehouse, difference_account, basic_rate):
        stock_entry.append('items', {
            'barcode': self.barcode,
            'serial_no': self.barcode,
            'item_code': self.item_code,
            'item_group': self.item_group,
            'basic_rate':basic_rate,
            'qty': 1,
            'uom': 'Nos',
            'conversion_factor': 1,
            'stock_uom': 'Nos',
            'expense_account': difference_account,
            't_warehouse': s_warehouse,
            's_warehouse': t_warehouse,
            'is_finished_item': 1 if index == 1 else 0,
            'set_basic_rate_manually': True
        })
        return stock_entry



    def check_manadatory_option(self):
        remaining_check_list = []
        for reading in self.nj_quality_readings:
            #get manadatory options of quality check
            if reading.quality_check:
                qc_reqd_options = [q.quality_check for q in frappe.db.get_list("Nj QC Options", {"mandatory":1, "parent":reading.quality_check}, 'quality_check')]
                #replace check name by name of check
                qc_reqd_options = map(get_name_of_check, qc_reqd_options)
                qc_reqd_options = list(qc_reqd_options)
                if len(qc_reqd_options) > 0:
                    #get check name list according to item group from nj quality checks
                    qc_list = [qc.check_name for qc in self.nj_quality_checks if qc.item_group == reading.item_group]
                    if len(qc_list) > 0 :
                        for qro in qc_reqd_options:
                            # add quality checks if options not selected for mandatory
                            if qro not in qc_list and reading.quality_check not in remaining_check_list:
                                remaining_check_list.append(reading.quality_check)
                    elif reading.quality_check not in remaining_check_list:
                        remaining_check_list.append(reading.quality_check)
            else:
                pass
                # frappe.throw(f" Quality check is missing")
                    
        if len(remaining_check_list) > 0 and remaining_check_list != None:
            frappe.throw(f" You have left the checks unmarked for  <b>{', '.join(remaining_check_list)} </b>. Please fill the necessary checks.")


    def stock_entry(self):
        new_jaisa_config=frappe.get_doc('NewJaisa Configuration')
        stock_entry = frappe.new_doc('Stock Entry')
        if self.inspection_type==new_jaisa_config.default_inspection_type:
           stock_entry.naming_series='SIQC-'
        else:
          stock_entry.naming_series='SEQC-'
        stock_entry.stock_entry_type = 'Repack'
        stock_entry.reference_type = 'NJ Quality Inspection'
        stock_entry.reference = self.name
        stock_entry.reference_serial_no = self.barcode
        stock_entry.company = frappe.db.get_single_value("Global Defaults", "default_company")

        for nj_readings in self.nj_quality_readings:
            if nj_readings.grade != 'Grade A' and nj_readings.item:
                warehouse = self.get_warehouse(serial_no=nj_readings.part_serial_no)
                items = self.get_source_and_target_items(reading = frappe._dict(nj_readings.as_dict())) 
                for index, item in enumerate(items):
                    stock_entry.append('items', {
                        'barcode': nj_readings.part_serial_no,
                        'serial_no': nj_readings.part_serial_no,
                        'item_code': item,
                        'item_group': nj_readings.item_group,
                        'basic_rate':self.get_basic_rate(reading = frappe._dict(nj_readings.as_dict())),
                        'qty': 1,
                        'uom': 'Nos',
                        'conversion_factor': 1,
                        'stock_uom': 'Nos',
                        'expense_account': get_stock_adjustment_account(stock_entry.company),
                        't_warehouse': warehouse if index == 1 else None,
                        's_warehouse': warehouse if index == 0 else None,
                        'is_finished_item': 1 if index == 1 else 0,
                        'set_basic_rate_manually': True
                    })
        if getattr(stock_entry, "items", False): # only create if row is added
            stock_entry.save()
            stock_entry.submit()

        # Update the Serial No
        if self.barcode and getattr(stock_entry, "items", False):
            serial_no_doc = frappe.get_doc('Serial No', self.barcode)

            removed_part_list_index = []
            for item in stock_entry.items:
                for part_index, part in enumerate(serial_no_doc.serial_no_component): # Part List
                    if item.s_warehouse:
                        # Source Warehouse -> Remove Part List
                        if item.item_code == part.item:
                            removed_part = serial_no_doc.serial_no_component[part_index]
                            removed_part_list_index.append(part_index)

                            # Add in `Past Part List`
                            serial_no_doc.append('past_part_list', {
                                "item_group": removed_part.item_group,
                                "item": removed_part.item,
                                "component_serial_no": removed_part.component_serial_no,
                                "grade": removed_part.grade,
                                "quantity": removed_part.quantity,
                                "image": removed_part.image,
                                "qi_reference": removed_part.qi_reference,
                                "is_available": removed_part.is_available
                            })
            
            # Sort indices in descending order to avoid issues when removing elements
            removed_part_list_index.sort(reverse=True)
            for index in removed_part_list_index:
                serial_no_doc.serial_no_component.pop(index)

            # Add `Part List`
            for index, item in enumerate(stock_entry.items):
                if item.t_warehouse:
                    old_item = self.get_new_and_old_item(stock_entry.items[index-1])
                    serial_no_doc.append('serial_no_component', {
                        "item_group": item.item_group,
                        "item": item.item_code,
                        "component_serial_no": item.serial_no,
                        "qi_reference": self.name,
                        "component_serial_no": item.serial_no,
                        "grade": old_item.grade,
                        "quantity" : 1 if old_item.is_available else 0,
                        "is_available": old_item.is_available
                    })
            for index, row in enumerate(serial_no_doc.serial_no_component):
                row.idx = index + 1
            serial_no_doc.save()
    

    def get_new_and_old_item(self, stock_item):
        for nj_readings in self.nj_quality_readings:
            if nj_readings.item == stock_item.item_code:
                return nj_readings
    
    def update_serial_no(self):
        pass



    def get_basic_rate(self, reading:frappe._dict=None) -> float:
        reading.serial_no = reading.part_serial_no
        basic_rate = get_basic_rate_for_remove_component(reading)
        return basic_rate
        print("basic rate ", basic_rate)

    def get_warehouse(self, serial_no:str=None):
        warehouse = frappe.db.get_value('Serial No', serial_no, 'warehouse')
        if warehouse:
            return warehouse
        warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse')
        if warehouse:
            return warehouse
        frappe.throw('Please set the <b>Default Warehouse</b> in the Stock Settings')
        
    def get_source_and_target_items(self, reading:frappe._dict=None) -> tuple:
        if reading.item:
            grade_list = frappe.db.get_all('Grade', pluck='name')
            for grade in grade_list:
                if grade and grade.upper() in reading.item:
                    if reading.grade:
                        item_grade = reading.grade
                    else:
                        item_grade = get_attribute_value_from_item(reading.item, 'Grade')
                    new_item = (reading.item).replace(grade.upper(), item_grade.upper())
                    if frappe.db.exists('Item', new_item):
                        return reading.item, new_item
                    else:
                        frappe.throw(f'The Item <b>{new_item}</b> is not exist')
            frappe.throw(f'Grade is Miss Matching please check in your <b>Grade</b> Doctype')
        else:
            frappe.throw('Item is not there in the NJ Readings')

    def get_nj_quality_readings_item_price(self):
    
        try:
            total_amount = 0
            total_prepared_value = 0
            price = 0
            prepared_value = 0
            for nj_qr in  self.nj_quality_readings:
                if nj_qr.item_group and nj_qr.grade and nj_qr.item:
                    item_group = frappe.get_doc('Item Group', nj_qr.item_group)
                    if nj_qr.grade == 'Grade A':
                        price = get_the_grade_a_item_price(nj_qr)
                        prepared_value = self.get_prepared_value(item_group, nj_qr, price)
                    else:
                        # price = get_price_from_item_group(item_group, nj_qr, parent_item_group = self.item_group)
                        price = self.get_actual_value(nj_reading=nj_qr.as_dict())
                        prepared_value = self.get_prepared_value(item_group, nj_qr, price)
                    total_amount += price
                    total_prepared_value += prepared_value
                    price = 0
                    print('total amount',total_amount)
                    print('preparedd value',total_prepared_value)
            self.assign_the_price_in_serial_no(total_amount, total_prepared_value)

        except Exception as ex:
            frappe.msgprint(f'Check the pricing part calculation \n {str(ex)}')

    def get_actual_value(self, nj_reading:frappe._dict) -> float:
        """
            This Funtion Calculate the Basic rate and actual rate how we are calculating in the `Machine Part Changes`
        """

        item_group = frappe.get_doc('Item Group', self.item_group)

        if nj_reading.item_group and nj_reading.item:
            for part in item_group.component_list:
                if part.component_name == nj_reading.item_group:
                    percentage = part.laptop_percentage_value
                    basic_rate = get_basic_rate_for_remove_component(nj_reading)
                    purchase_cost = self.get_purchase_cost_from_serial_number()
                    actual_rate = self.get_actual_rate_and_basic_rate_based_on_grade(nj_reading=nj_reading, basic_rate=basic_rate, main_group_percentage=percentage, purchase_cost=purchase_cost)
                    return actual_rate
            return 0.0
        else:
            return 0.0

    def get_actual_rate_and_basic_rate_based_on_grade(self, **kwargs):
        """
            This same funtion is there in the `Machine Part Changed` from there its taking the reference
        """
        actual_rate = 0.0
        nj_reading = kwargs.get("nj_reading")

        if nj_reading.get("grade") == 'Grade A':
            return kwargs.get("basic_rate")
        
        basic_rate = get_correct_basic_rate(kwargs.get("basic_rate"), kwargs.get("purchase_cost"), kwargs.get("main_group_percentage"))
        
        if nj_reading.grade == 'Grade C' or nj_reading.grade == 'Grade D':
            item_group = frappe.get_doc('Item Group', nj_reading.item_group)

            if item_group.allowed_grade:
                for allowed_grade in item_group.allowed_grade:
                    if allowed_grade.grade == nj_reading.grade:
                        actual_rate = basic_rate * (allowed_grade.value / 100)
                        return actual_rate
            return 0.0
        else:
            return 0.0

    def get_purchase_cost_from_serial_number(self) -> float:
        
        current_price, purchase_price = frappe.db.get_value(
                                                                "Serial No",
                                                                self.barcode,
                                                                ['current_price', 'purchase_price']
                                                            )
        if current_price:
            return current_price
        else:
            return purchase_price



    def assign_the_price_in_serial_no(self, total_actual_value, total_prepared_value):
        serial_doc = frappe.get_doc('Serial No', self.barcode)

        if int(serial_doc.current_price) == 0:
            try:
                purchase_receipt_serial_no = frappe.get_last_doc('Serial No', filters={'item_code':serial_doc.item_code, 'purchase_document_type':'Purchase Receipt'})
                serial_doc.purchase_price = purchase_receipt_serial_no.purchase_rate
                serial_doc.preferred_purchase_price_ = purchase_receipt_serial_no.purchase_rate - total_prepared_value
                serial_doc.current_price = purchase_receipt_serial_no.purchase_rate - total_prepared_value
            except frappe.exceptions.DoesNotExistError:
                serial_doc.purchase_price = serial_doc.purchase_rate
                serial_doc.preferred_purchase_price_ = serial_doc.purchase_rate - total_prepared_value
                serial_doc.current_price = serial_doc.purchase_rate - total_prepared_value
            except Exception as ex:
                frappe.throw(str(ex))
        else:
            serial_doc.current_price = serial_doc.purchase_price - total_prepared_value

        serial_doc.save()
        

    def get_prepared_value(self, item_group, nj_qr, actual_value):
        
        value = 0
        for allowed_grade in item_group.allowed_grade:
            if allowed_grade.grade == nj_qr.grade:
                try:
                    value = actual_value * (int(allowed_grade.part_value_percentage) / 100 )
                    return value
                    print("value",value)
                except:
                    return 0
        return 0

def get_name_of_check(qc):
    return frappe.db.get_value('NJ QC Check List', {'name':qc},'name_of_check')



def validate(doc,method=None):
    validation_for_quality_checks_not_found(doc)


def validation_for_quality_checks_not_found(doc):
    for qc in doc.nj_quality_readings:
        if qc.quality_check == ' ' or None:
            frappe.msgprint(f"Link is not valid for nj quality inspection")



@frappe.whitelist()
def get_grade(total_score=None, item_group=None):
    if item_group and total_score != None:
        if isinstance(total_score, str):
            total_score = json.loads(total_score)
        grade_data = frappe.db.get_all("Item group Grades", {'parent': item_group},['min_total_score','max_total_score', 'grade'])
        for g in grade_data:
            if g.min_total_score <= total_score and g.max_total_score >= total_score:
                return g.grade 
            

@frappe.whitelist()
def get_qc_options(quality_check=None, nj_quality_checks=None, item_group=None):
    if quality_check:
        title_data = frappe.db.get_all("NJ Quality Checks", {'name': quality_check}, ['inspection_type'])
        title_data =[t['inspection_type']+' '+ item_group for t in title_data]
        nj_qc_options = frappe.db.sql(f""" select quality_check, mandatory from `tabNj QC Options` where parent = '{quality_check}' order by idx""")
        nj_qc_dict= dict(nj_qc_options)
        qc_list = list(nj_qc_dict.keys())
        if qc_list and len(qc_list) > 0:
            data = []
            for qc in qc_list:
                qc_check_data = frappe.db.sql(f""" select check_options,score, active from `tabQC Options` where parent = '{qc}' order by idx""", as_dict=1)
                qc_options_list= [i['check_options'] for i in qc_check_data]
                qc_options_list.insert(0,' ')
                qc_dict = {}
                field_name = (qc.lower()).replace(' ', '_')
                frappe.db.set_value('NJ QC Check List', qc, 'field_name', field_name)
                name_of_check = frappe.db.get_value('NJ QC Check List', {'field_name':field_name},'name_of_check')
               
                #add asteric on label to show manadatory field 
                if nj_qc_dict[qc] and name_of_check:
                    name_of_check += "*"

                row = {'label': name_of_check, 'fieldname':field_name, 'fieldtype':'Select', 'options':qc_options_list}
                if nj_quality_checks and len(nj_quality_checks) > 0:
                    default_qc_option = get_last_qc_value(nj_quality_checks, field_name, item_group)
                    if default_qc_option is not None:
                        row.update({'default':default_qc_option})
                main_list= []
                for val in qc_check_data:
                    main_row = {}
                    main_row.update(val)
                    if main_row not in main_list:
                        main_list.append(main_row)
                row.update({'score':main_list})
                # row.update({'title': 'tooltip'})
                qc_dict.update(row)
                data.append(qc_dict)
                check_name = frappe.db.get_value('NJ QC Check List', {'field_name':field_name},'name')
                desc = get_desc_from_qc_check_list(field_name)
            result ={'data':data, 'title':title_data[0], 'check_name':check_name, 'description':desc }
            return result
        else:
            frappe.msgprint(f"Attributes of quality checks not found")

def get_last_qc_value(nj_quality_checks, qc, item_group):
    nj_quality_checks = json.loads(nj_quality_checks)
    if len(nj_quality_checks) > 0:
        for c in nj_quality_checks:
            if c['item_group']== item_group and c['checks'] == qc:
                return c['options']

def get_score_weightage(check, option):
    qc_check_data = frappe.db.get_list('QC Options', filters={'parent':check, 'check_options':option},fields=['score', 'active'])
    if len(qc_check_data) > 0 :
        return qc_check_data[0]

@frappe.whitelist()
def get_qc_check_details(data=None, nj_quality_checks=None, item_group=None):
    print(f"data {data} nj_quality_checks {nj_quality_checks } item_group {item_group}")
    nj_quality_checks_list= []
    if nj_quality_checks != None:
        if isinstance(nj_quality_checks, str):
            nj_quality_checks = json.loads(nj_quality_checks)
        for quality_check in nj_quality_checks:
            nj_quality_checks_dict = {}
            for key in ['item_group', 'checks', 'options','score','active','check_name', 'description' ]:
                if key in quality_check:
                    nj_quality_checks_dict[key] = quality_check[key]
            nj_quality_checks_list.append( nj_quality_checks_dict)
    if data:
        data = json.loads(data)
        for k,v in data.items():
            row_dict = {}
            check_name = frappe.db.get_value('NJ QC Check List', {'field_name':k},'name')
            desc=get_desc_from_qc_check_list(check_name)
            name_of_check = frappe.db.get_value('NJ QC Check List', {'field_name':k},'name_of_check')
            if nj_quality_checks == None:
                row_dict.update({'item_group' : item_group , 'checks' : k, 'options' : data[k], 'check_name': name_of_check, 'description' : desc})
                score_weightage = get_score_weightage(check_name, data[k] )
                if len(score_weightage) > 0:
                    row_dict.update({'score' : float( score_weightage['score']), 'active': float(score_weightage['active']) })
                if row_dict not in nj_quality_checks_list:
                    nj_quality_checks_list.append(row_dict)
            else:
                for q_check in nj_quality_checks_list:
                    if q_check['item_group'] == item_group and q_check['checks'] == k:
                        q_check['options'] = data[q_check['checks']]
                        q_check['check_name'] = name_of_check
                        q_check['description'] = desc
                        score_weightage = get_score_weightage(check_name, q_check['options'] )
                        if len(score_weightage) > 0:
                            q_check['score'] = float( score_weightage['score'])
                            q_check['active'] = float(score_weightage['active'])
                    elif ( q_check['checks'] == k and item_group != q_check['item_group']) or (q_check['checks'] != k and item_group == q_check['item_group']) or ( q_check['checks'] != k and item_group != q_check['item_group']):
                        row_dict = {}
                        row_dict.update( {'item_group':item_group,'checks':k, 'options':v})
                        if check_name:
                            row_dict.update({'check_name': name_of_check,'description':desc})
                            score_weightage = get_score_weightage(check_name, v)
                            if len(score_weightage) > 0:
                                row_dict.update({'score':float(score_weightage['score']),'active': float(score_weightage['active'])}) 
                        if row_dict not in nj_quality_checks_list:
                            nj_quality_checks_list.append(row_dict)
                    
        nj_quality_checks_list = remove_duplicate_dict(nj_quality_checks_list)      
        seen_combinations = set()
        print(f"nj_quality_checks_list {nj_quality_checks_list}")

        # Initialize a result list
        result = []

        # Iterate through the data and filter out duplicates based on 'item_group' and 'check_name'
        for item in nj_quality_checks_list:
            combination = (item['item_group'], item['check_name'])
            if combination not in seen_combinations:
                result.append(item)
                seen_combinations.add(combination)
        return result
    


def get_desc_from_qc_check_list(check):
    return frappe.db.get_value('NJ QC Check List', {'name':check},'description')

#remove duplicate element check even all keys and their values 
def remove_duplicate_dict(nj_quality_checks_list):
    seen = set()
    new_l = []
    for d in nj_quality_checks_list:
        t = tuple(d.items())
        if t not in seen:
            seen.add(t)
            new_l.append(d)
    return new_l

def change_key_of_dict(k):
    words = k.split('_')

    # Capitalize the first letter of each word and join them with a space
    k = ' '.join(word.capitalize() for word in words)
    return k

@frappe.whitelist()
def fetch_nj_qlty_readings(doc):
    try:
       Quality_reading=[]
       doc = json.loads(doc)
       if doc.get("barcode"):
           item_code = frappe.db.get_value("Serial No", {'name': doc.get("barcode")}, 'item_code')
           itm_template = frappe.db.get_value("Item", {'name': item_code}, 'variant_of')
           #frappe.msgprint(f"{itm_template}")
           if itm_template:
              itm_wzrd = frappe.db.get_value("Item", {'name': itm_template}, 'reference')
              if itm_wzrd:
                 itm_wzrd_doc = frappe.get_doc("Item Wizards", itm_wzrd)
        #quality_inspection = frappe.new_doc("Quality Inspection")
       serial_no_doc=frappe.get_doc('Serial No',doc.get("barcode"))
       serial_no=frappe.db.get_list('Serial No Component',
       filters={'parent':doc.get("barcode")},fields=['item_group'])
       if serial_no:
          #quality_inspection.nj_quality_readings=[]
          for i in serial_no_doc.serial_no_component:
              nj_quality_checks=frappe.db.get_value('NJ Quality Checks',
              {'inspection_type':doc.get("inspection_type"),'item_group':i.item_group},['name'])
              Quality_reading.append({"item_group":i.item_group,"quality_check":nj_quality_checks})
          return Quality_reading
       if not serial_no:
          for compo in itm_wzrd_doc.component:
              #frappe.msgprint(f"{compo.component_type}")
              nj_quality_checks=frappe.db.get_value('NJ Quality Checks',
               {'inspection_type':doc.get("inspection_type"),'item_group':compo.component_type},['name'])
              Quality_reading.append({"item_group":compo.component_type,"quality_check":nj_quality_checks})
          return Quality_reading
    except Exception as ex:
        #frappe.log_error(frappe.get_traceback(), 'Item Wizards and Serial None ')
        return False


#quality_readings_quality_check_clm_update_on_inspection_type
# @frappe.whitelist()          
# def clm_update_on_inspection_type(tbl_data,inspection_type):
#    # doc = json.loads(doc)
#     dicte=[]
#     #for i in tbl_data:
#     frappe.msgprint(f"{tbl_data}")
#     for dict_item in tbl_data:
#         for key in dict_item:
#             frappe.msgprint(f"{dict_item[key]}")
#     #tbl_list.append(tbl_data)
#     # if tbl_data:
#             Quality_checks=[i.name for i in frappe.db.get_list("NJ Quality Checks",
#          {"inspection_type":inspection_type,"item_group":dict_item[key]},'name')]
#             return Quality_checks
    #     dicte.append({"item_group":tbl_data,"quality_check":Quality_checks[0] if Quality_checks else "" })
    #     return dicte

@frappe.whitelist()  
# def get_quality_checks_data(quality_readings, inspection_type, serial_number):
def get_quality_checks_data(doc):
    import json
    doc = json.loads(doc)   
    quality_check_list=frappe.db.get_list("NJ Quality Checks",{"inspection_type":doc.get('inspection_type')},['name','item_group'])
    if len(doc.get('nj_quality_readings')) >0 :
        for qr in doc.get('nj_quality_readings'):
            if len(quality_check_list) > 0 :
                for qc in quality_check_list:
                    if qr['item_group']== qc['item_group']:
                        qr['quality_check'] = qc['name']
            else:
                qr['quality_check'] = ' '
           
            if qr['item_group'] not in [i['item_group'] for i in quality_check_list] :
                qr['quality_check'] = ' '
    return doc.get('nj_quality_readings')

@frappe.whitelist()
def get_qc_score():
    pass

def on_submit(doc,method=None):
    
    # set_item_name_for_part_serial_no(doc)
    set_serial_no_component_details(doc)
    
def set_item_name_for_part_serial_no(doc):
    sn_doc = frappe.get_doc("Serial No", doc.bios_serial_number)
    #move serial no component data to past part list
    if len(sn_doc.serial_no_component) > 0:
        sn_row = {}
        for sn in sn_doc.serial_no_component:
            sn_row.update({'item_group':sn.item_group, 'item':sn.item, 'component_serial_no':sn.component_serial_no, 'grade': sn.grade, 'qi_reference':doc.name})

            
            sn_doc.append("past_part_list", sn_row)
    sn_doc.serial_no_component = []
    for reading in doc.nj_quality_readings:
        #frappe.msgprint(f"reading.item {reading.item}")
        row = {}
        #if reading.item and reading.part_serial_no and reading.grade:
        if reading.item_group:
            current_grade = frappe.db.get_value("Item Variant Attribute", {'parent':reading.item, 'attribute':"Grade"}, 'attribute_value')
            new_item_name = ''
            if current_grade and reading.grade:
                if current_grade in reading.item:
                    new_item_name = (reading.item).replace(current_grade, reading.grade)
                    # print(f" if new_item_name {new_item_name}")
                else:
                    grade_name = frappe.db.get_value("Item Attribute Value", {'attribute_value': current_grade, 'parent':'Grade'}, 'abbr')
                    print(f"@@@@@@@@@@@@@@@ grade_name {grade_name}")
                    new_item_name = (reading.item).replace(grade_name, reading.grade) if grade_name else ''
                    # print(f" else new_item_name {new_item_name}")
            else:
                pass
                #frappe.throw(f"Grade attribute is not found for item {reading.item} ")
            frappe.db.sql("""Update `tabSerial No` set item_code = '{0}', item_name = '{0}', description = '{0}' where name = '{1}'""".format(new_item_name, reading.part_serial_no))
            frappe.db.commit()

            #set component data on barcode serial no
            row.update({'item_group':reading.item_group, 'item':reading.item, 'component_serial_no':reading.part_serial_no, 'grade': reading.grade})
                        # Check if the dictionary with the same ID exists in the list

            
            
            
            # make empty and add new record in serial no component
           
            sn_doc.append("serial_no_component", row)




            # if len(sn_doc.serial_no_component) == 0:
            #     if row['component_serial_no'] not in sn_doc.serial_no_component:
            #         sn_doc.append("serial_no_component", row)
            #         print(f"if row {row}")
            # else:
            #     for compo in sn_doc.serial_no_component:
            #         if  compo.component_serial_no and compo.component_serial_no == reading.part_serial_no:
            #             print(f" compo.component_serial_no {compo.component_serial_no}")
            #             compo.grade = reading.grade
            #             compo.item = reading.item
            #             print(f" else if row {row}")
            #         elif reading.item_group not in [compo.item_group for compo in sn_doc.serial_no_component]:
            #             sn_doc.append("serial_no_component", row)
            #             print(f"else else row {row}")

                   

    sn_doc.save()
            # data_list = sn_doc.serial_no_component
            # print(f"data_list {data_list.as_dict()}")
            # existing_dict = next((item for item in data_list if item["item"] == row["item"]), None)

            # if existing_dict:
            #     # Update values if the dictionary already exists
            #     existing_dict.update(row)
            # else:
            #     # Add the new dictionary if it doesn't exist
            #     # (sn_doc.serial_no_component).append(row)
            # # if row not in sn_doc.serial_no_component:
            #     sn_doc.append("serial_no_component", row)
            #     sn_doc.save()
            

    

def get_the_grade_a_item_price(nj_qr):
    price = get_price_from_serial_no(nj_qr)
    if price:
        return price
    price = get_price_from_stock_ledger(nj_qr)
    if price:
        return price
    
    price = get_price_from_item_template(nj_qr)
    if price:
        return price
    return 0


def get_price_from_item_template(nj_qr):
    try:
        variant_of = frappe.db.get_value('Item', nj_qr.item, 'variant_of')
        valuation_rate = frappe.db.get_value('Item', variant_of, 'valuation_rate')
        return valuation_rate
    except:
        return None

def get_price_from_stock_ledger(nj_qr):
    try:
        stock_ledger = frappe.get_last_doc('Stock Ledger Entry', filters={'item_code' : nj_qr.item, 'docstatus':1})
        return stock_ledger.valuation_rate
    except:
        return None

def get_price_from_serial_no(nj_qr):
    try:
        serial_doc = frappe.get_doc('Serial No', nj_qr.part_serial_no)
        return serial_doc.purchase_rate
    except:
        return None

def get_price_from_item_group(doc, nj_qr, parent_item_group=None):

    for allowed_grade in doc.allowed_grade:
        if nj_qr.grade == allowed_grade.grade:
            return allowed_grade.actual_value    
    return 0


def set_serial_no_component_details(doc):
    # if doc.inspection_type == "IQC":
    serial_no_doc = frappe.get_doc("Serial No", doc.bios_serial_number)
    for reading in (doc.nj_quality_readings):
        if reading.item_group not in  [s.item_group for s in serial_no_doc.serial_no_component] :
            row = serial_no_doc.append('serial_no_component', {})
            row.item = reading.item
            row.item_group = reading.item_group
            row.grade = reading.grade
            row.is_available=reading.is_available
            row.quantity = 1  if reading.is_available else 0
            row.qi_reference = doc.name
            serial_no_doc.save() 
        else:
            for sn in serial_no_doc.serial_no_component:
                if reading.item_group == sn.item_group :
                    if sn.component_serial_no == None or  sn.component_serial_no == '':
                        frappe.msgprint(reading.is_available)
                        sn.item = reading.item
                        sn.grade = reading.grade
                        sn.component_serial_no = reading.part_serial_no
                        sn.is_available=reading.is_available
                        sn.quantity = 1 if reading.is_available else 0
                        sn.qi_reference = doc.name
                        # print(f"sn {sn.as_dict()}")
                        serial_no_doc.save() 
                    elif reading.part_serial_no not in [s.component_serial_no for s in serial_no_doc.serial_no_component]:
                        sn.item = reading.item
                        sn.grade = reading.grade
                        sn.component_serial_no = reading.part_serial_no
                        sn.is_available=reading.is_available
                        sn.quantity = 1  if reading.is_available else 0
                        # print(f"sn {sn.as_dict()}")
                        serial_no_doc.save() 
                    elif reading.part_serial_no == sn.component_serial_no:
                        sn.item = reading.item
                        sn.grade = reading.grade
                        sn.is_available=reading.is_available
                        sn.quantity = 1  if reading.is_available else 0
                        sn.qi_reference = doc.name
                        serial_no_doc.save()
                    else:
                        print(f" elseeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")

                

                    # frappe.db.sql("""" Update """)

            # print(f" else {reading.item_group}  ")

            # serial_no_doc.serial_no_component[index] = source_dict
        # parent_doc = frappe.get_doc("ParentDoctype", "parent_doc_name")

        # source_child_table = doc.nj_quality_readings
        # print(f"//// source_child_table {source_child_table}")
        # target_child_table = serial_no_doc.serial_no_component
        # import copy
        # serial_no_doc.serial_no_component = copy.deepcopy(source_child_table)
        
        # parent_doc.save()
        # serial_no_doc.serial_no_component = doc.nj_quality_readings
        # print(f"serial_no_doc.serial_no_component {serial_no_doc.serial_no_component}")
        # serial_no_doc.save()
        # for reading in doc.nj_quality_readings:
        #     print(f"serial_no_doc.serial_no_component {(serial_no_doc.serial_no_component)}")
        #     if len(serial_no_doc.serial_no_component) == 0:
        #         print(f"if reading {reading.grade}")
        #         row = serial_no_doc.append('serial_no_component', {})
        #         row.item_group = reading.item_group
        #         row.grade = reading.grade
        #         row.quantity = 1  if reading.is_available else 0
        #         serial_no_doc.save() 
        #         print(f"1st if {[s.item_group for s in serial_no_doc.serial_no_component]}")
        #     elif reading.item_group not in  [s.item_group for s in serial_no_doc.serial_no_component] :
        #         print(f"elif reading {reading.grade}")
        #         row = serial_no_doc.append('serial_no_component', {})
        #         row.item_group = reading.item_group
        #         row.grade = reading.grade
        #         row.quantity = 1  if reading.is_available else 0
        #         serial_no_doc.save()  
        #         print(f"1st elif {[s.item_group for s in serial_no_doc.serial_no_component]}")
        #     else:
        #         for component in serial_no_doc.serial_no_component:
        #             if reading.item_group == component.item_group:
        #                 print(f"component  reading {reading.grade}")
        #                 component.grade = reading.grade if reading.grade else  ' '
        #                 component.quantity = 1  if reading.is_available else 0
        #                 serial_no_doc.save()

# @frappe.whitelist()
# def camera_recoder():
#     vid_capture = cv2.VideoCapture(0)
#     vid_cod = cv2.VideoWriter_fourcc(*'XVID')
#     output = cv2.VideoWriter("videos/cam_video.mp4", vid_cod, 20.0, (640,480))
#     while(True):
#         ret,frame = vid_capture.read()
#         cv2.imshow("My cam video", frame)
#         output.write(frame)
#         if cv2.waitKey(1) &0XFF == ord('x'):
#             break
#     vid_capture.release()
#     output.release()
#     #cv2.destroyAllWindows()


@frappe.whitelist()
def set_data_inspection_type_data_dynamicaly():
    inspection_type=[i.name for i in frappe.db.get_list("Inspection Type",'name')]
    return inspection_type


# get item details from barcode(serial no)- code changes done by Anuradha(7-12-23)
@frappe.whitelist()
def get_barcode_details(barcode,inspection_type):
    nj_quality_reading={}
    try:
        serial_no = frappe.get_doc('Serial No', barcode)
        nj_quality_check=frappe.db.get_value('NJ Quality Checks',{"inspection_type":inspection_type,"item_group":serial_no.item_group},'name')
        nj_quality_reading.update({"item_code":serial_no.item_code,"item_group":serial_no.item_group,"quality_check":nj_quality_check, "name":serial_no.name})
        return nj_quality_reading
    except:
        return False
    

#function not in use
# def decode_svg_to_code(barcode_data):
#     import re
#     pattern = r'<text[^>]*>(.*?)</text>'
#     match = re.search(pattern, barcode_data)
#     if match:
#         barcode_code = match.group(1)
#         return barcode_code
#     else:
#         return None




@frappe.whitelist()
def get_valuation_rate(doc:str, row:str) -> dict:
    '''
    This funtion returns a dict with contains of the valuation rate and other details

    :param doc:str its contains the whole form data.
	:param row:str its contains the whole row data of `NJ Quality Readings`.
    '''
    doc = frappe._dict(json.loads(doc))
    row = frappe._dict(json.loads(row))

    
    template = frappe._dict({
        'valuation_rate': 0,
        'grade_a_rate': 0,
        'grade_c_rate': 0,
        'grade_d_rate':0
    })

    valuation_rate = get_valuation_rate_data(doc, row)
    template.valuation_rate = valuation_rate
    grade_a_rate = get_grade_a_rate(doc.item_group, row.item_group, valuation_rate)
    template.grade_a_rate = grade_a_rate
    
    grade_c_rate, grade_d_rate  = get_grade_c_and_d_rate(row.item_group, grade_a_rate)
    template.grade_c_rate = grade_c_rate
    template.grade_d_rate = grade_d_rate

    return template

def get_valuation_rate_data(doc, row):
    valuation_rate = 0
    if row.part_serial_no:
        '''Getting valuation rate from the Serial No'''
        valuation_rate = get_valuation_rate_from_serial_no(row.part_serial_no)
        if valuation_rate:
            return valuation_rate
    if not valuation_rate:
        '''Getting valuation rate from the `Stock Leadger Entry`'''
        valuation_rate = get_valuation_rate_from_stock_ledger_entry(row.item)
        if valuation_rate:
            return valuation_rate
    if not valuation_rate:
        ''' Get the valuation rate from the `Item` Template '''
        valuation_rate = get_valuation_rate_from_item(row.item)
        return valuation_rate
    return valuation_rate

def get_valuation_rate_from_serial_no(name:str) -> float:
    '''
    Getting the Rate of the item from the `Serial No`

    param name:str Name of the `Serial No` doctype

    Returns:
        return the Incoming Rate or Purchase Rate of that item
    '''
    purchase_document_type, purchase_rate = frappe.db.get_value('Serial No', name, ['purchase_document_type', 'purchase_rate'])
    if purchase_document_type == 'Purchase Receipt':
        return purchase_rate
    return 0.0


def get_valuation_rate_from_stock_ledger_entry(item:str) -> float:
    '''
    First Get the Default Warehouse from the `Stock Settings` and find the recently added item in the Warehouse and get the valuation rate
    If default ware house is not there getting item recently added at any Warehouse

    param: item:str `Item code`
    '''
    default_warehouse = timezone = frappe.db.get_single_value('Stock Settings', 'default_warehouse')
    valuation_rate = 0.0
    if default_warehouse:
        sle = frappe.db.sql(
            f'''
                SELECT * FROM `tabStock Ledger Entry`
                WHERE item_code = '{item}' AND warehouse = '{default_warehouse}' AND docstatus = 1
                ORDER BY creation DESC
                LIMIT 1
            ''',
            as_dict=1
        )
    else:
        sle = frappe.db.sql(
            f'''
                SELECT * FROM `tabStock Ledger Entry`
                WHERE item_code = '{item}' AND docstatus = 1
                ORDER BY creation DESC
                LIMIT 1
            ''',
            as_dict=1
        )

    if sle:
        sle = sle[0]
        return sle.valuation_rate
    return valuation_rate


def get_valuation_rate_from_item(item_code:str) -> float:
    '''
    Get the valuation rate from the item template

    param: item_code:str `Name of the Item doctype`
    '''
    variant_of = frappe.db.get_value('Item', item_code, 'variant_of')
    valuation_rate = frappe.db.get_value('Item', variant_of, 'valuation_rate') or 0.0

    return valuation_rate


def get_grade_a_rate(main_item_group:str, child_item_group:str, valuation_rate:float) -> float:
    '''
    In the Main item group checking the partl list and find the Child Item group's Laptop Percentage Value find the percentage of valuation rate

    param: main_item_group:str Main Item Group
    param: child_item_group:str Child Item Group
    param: valuation_rate:float Valuation rate
    '''
    item_group_doc = frappe.get_doc(
        'Item Group',
        main_item_group
    )
    grade_a_rate = 0.0
    for part_list in item_group_doc.component_list:
        if part_list.component_name == child_item_group:
            grade_a_rate = valuation_rate * (part_list.laptop_percentage_value/100)
            return grade_a_rate
    return grade_a_rate


def get_grade_c_and_d_rate(item_group:str, rate:float) -> float:
    '''
    Getting the Item Group, there is Allowed Grade there we can get the Grade C & Grade D percentage

    param: item_group:str Item Group Name
    param rate:float rate of tje percentage
    '''
    grade_c_rate = grade_d_rate = 0.0

    item_group_doc = frappe.get_doc('Item Group', item_group)

    for allowed_grade in item_group_doc.allowed_grade:
        if allowed_grade.grade == 'Grade C':
            grade_c_rate = get_c_or_d_rate(allowed_grade.value or 0.0, eval(allowed_grade.part_value_percentage) or 0.0, rate )
        elif allowed_grade.grade == 'Grade D':
            grade_c_rate = get_c_or_d_rate(allowed_grade.value or 0.0, eval(allowed_grade.part_value_percentage) or 0.0, rate )
    return grade_c_rate, grade_d_rate

def get_c_or_d_rate(percentage:float, part_value_percentage:float, rate:float) -> float:

    if percentage:
        percentage_grade_rate = rate * (percentage/100)

        if percentage_grade_rate:
            part_value_percentage_grade_rate = percentage_grade_rate * (part_value_percentage/100) or 1
            grade_rate = percentage_grade_rate * part_value_percentage_grade_rate
            return grade_rate
        else:
            return percentage_grade_rate
    else:
        frappe.msgprint('In allowed grade percentage value is zero')
        return 0
    


def get_stock_adjustment_account(company):
		stck_adjstment_accnt = frappe.db.get_value('Company', {'name': company}, 'stock_adjustment_account')
		return stck_adjstment_accnt if stck_adjstment_accnt else ''