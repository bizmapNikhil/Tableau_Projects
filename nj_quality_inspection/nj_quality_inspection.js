var quality_check_data

// cur_dialog.fields_dict.battery_check.$input.attr('title', 'New Tooltip Text')

frappe.ui.form.on("Nj Quality Readings", {
	
	total_score:function(frm, cdt,cdn){
		var child = locals[cdt][cdn];
		set_grade(child, frm)

	},
	item_group:function(frm,cdt,cdn){
		var child = locals[cdt][cdn];
		console.log("child++++",child.item_group)
	},

    // before_save(frm){
	// 	if(frm.doc.item_code){
	// 	frappe.call({
	// 		method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.fetch_nj_qlty_readings",
	// 		args: {
	// 			'doc':frm.doc
	// 		},
	// 		callback: function(r) {
	// 			console.log("item template varaints", r)
				
	// 		}
	// 	});
	//  }	
	// },
    check_button: function(frm, cdt,cdn){
        var child = locals[cdt][cdn];
		if(child.quality_check){
		  if(child.item_group){
			// console.log("frm.doc.nj_quality_checks", frm.doc.nj_quality_checks)
            frappe.call({
				method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.get_qc_options",
				args: {'quality_check':child.quality_check,
				"nj_quality_checks":frm.doc.nj_quality_checks,
				"item_group": child.item_group
				},
				callback: function(r) {
					console.log("get_qc_options r.message", r.message)
					if(r.message){
						$.each(r.message.data || [], function(i, d) { 
							if((d.label).includes('*')){
								d.label = (d.label).replace(/[*]/g, '') + "<span style='color:red'>" + '*' + "</span>";
							}

						});
						
						quality_check_data = r.message
						var d = new frappe.ui.Dialog({
							title: r.message.title,
							fields: r.message.data,
							static:true,
							backdrop:'static',
							primary_action: function(values) {
								var data = d.get_values();
								console.log('ddddddddd data',data, frm.doc.nj_quality_checks)
								
								frappe.call({
									method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.get_qc_check_details",
									args: {'data':data,
									'nj_quality_checks': frm.doc.nj_quality_checks,
									'item_group': child.item_group

									},
									callback: function(r) {
										console.log("get_qc_check_details   r",r.message)
										// console.log(" quality_check_data.main ", quality_check_data.main['checks'])
										if(r.message){
											cur_frm.clear_table("nj_quality_checks");
											r.message.forEach(function(element) {
													var r = frm.add_child('nj_quality_checks');
													//console.log(" element.check_name ", element.description)
													r.check_name = element.check_name
													r.checks = element.checks
													r.item_group = element.item_group
													r.options = element.options
													r.description = element.description
													r.score =  parseFloat(element.score)
													r.weightage =  parseFloat(element.active)
													//Calculate total score
													// total_score += r.score

													frm.refresh_field("nj_quality_checks")
											});
											
										}
										// child.total_score = total_score
										frm.refresh_field("nj_quality_readings")
									}
								})
								// }
								
								d.hide();

							},
							secondary_action:function(values){
								d.hide();
							},
							primary_action_label: __('Save'),
							secondary_action_label: __('Cancel')

													
						});
						
						d.show();
						
					}
					
				}
			});
		  }
        } 
		else{
			frappe.msgprint(__("Quality check required for item group <b>{0}</b> .", [child.item_group]));
		}
	},
	set_qc_score(frm){
		frappe.call({
			method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.get_qc_score",
			args: {
				'nj_quality_checks': frm.doc.nj_quality_checks
			},
			callback: function(r) {
				console.log("r",r.message)
				if(r.message){
					
				}
			}
		})
	}
	
});


function set_grade(qr, frm){
		frappe.call({
			method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.get_grade",
			args: {
				'total_score': qr.total_score,
				'item_group': qr.item_group
			},
			callback: function(r) {
				console.log("r",r.message)
				if(r.message){
					qr.grade = r.message
					frm.refresh_field("nj_quality_readings");
				}
				// else{
				// 	frappe.msgprint(__("Grade not found for item group <b>{0}</b> .", [qr.item_group]));
				// }
			}
		})
}

// Doctype Quality Inspection
frappe.ui.form.on("NJ Quality Inspection", {
	before_save:function(frm){
		// if((frm.doc.nj_quality_readings).length >0){
			$.each(frm.doc.nj_quality_readings, function(index, qr) {
				var mult_score_weightage  = 0;
				var total_weightage = 0;
				
				$.each(frm.doc.nj_quality_checks, function(index, qc) {
					if (qc['item_group'] == qr['item_group']){
						mult_score_weightage = mult_score_weightage + qc['score'] * qc['weightage']
						total_weightage = total_weightage + qc['weightage']
					}
				});
				console.log('total scor',total_weightage)
				//console.log("num",total_weightage <1 ? 1:total_weightage)
				if (total_weightage > 0){
					qr.total_score = mult_score_weightage/total_weightage
				}
				// else {
				// 	qr.total_score = 0
				// }
					
				// set_grade(qr, frm)
				// if (frm.doc.nj_quality_checks && frm.doc.nj_quality_checks.length > 0) {
				// 	// Check if the item group exists in the Nj quality table
				// 	const itemGroupExists = frm.doc.nj_quality_checks.some(check => check.item_group);
				
				// 	if (itemGroupExists) {
				// 		set_grade(qr, frm);
				// 	}
				// }
				if (frm.doc.nj_quality_checks && frm.doc.nj_quality_checks.length > 0) {
					frm.doc.nj_quality_checks.forEach(check => {
						if (check.item_group) {
							// Find the matching item group in nj_quality_readings
							const matchingItemgr = frm.doc.nj_quality_readings.find(item => item.item_group === check.item_group);
							if (matchingItemgr) {
								set_grade(qr, frm);
							}
							else{
								check.grade = ''
								frm.refresh_field("nj_quality_readings");

							}
						}
					});
				}
				
				
				

			});
		// }
		
	},
	check_quality_checks_link_in_nj_quality_readings(frm){
		if (frm.doc.nj_quality_readings.length){
			for(const njqr of frm.doc.nj_quality_readings){
				if (njqr.quality_check == " " || njqr.quality_check == ""){
					njqr.quality_check = null
				}
			}
		}
	},
	after_save(frm){
		set_valuation_rate(frm);
	},
	refresh:function(frm){
		frm.trigger('set_camera_button')
		frm.trigger('stop_camera_button')
		//get_itm_code_on_barcode(frm)



		$.each(frm.doc.nj_quality_checks,function(index, r) {
			frappe.db.get_value('NJ QC Check List', r.check_name, 'description') .then(p => {
				console.log('p.description',p.description)
				if(p.description){
                    r.description=p.description;
					cur_frm.refresh_fields("nj_quality_checks")
	            }
												
		    })
											
			})
	},
	barcode:function(frm){
		if(frm.doc.barcode){
			frm.set_value('bios_serial_number', frm.doc.barcode)
		}
		else{
			frm.set_value('bios_serial_number', " ")
		}
		get_itm_code_on_barcode(frm)
		fill_nj_quality_reading_from_serial_or_itm_wizard(frm)		
	},
	item_group(frm){
		setTimeout(() => {  
			add_item_group_and_Quality_check(frm)
		 }, 1000);
	 },
	onload:function(frm){
		// set_data_inspection_type_data_dynamicaly(frm)
	},
	inspection_type(frm){
		if(frm.doc.inspection_type){
			set_quality_checks_as_per_inspection_type(frm)
			// set_abbr(frm)
		}
	},
	setup:function(frm){
		// set_data_inspection_type_data_dynamicaly(frm)
	},
	validate:function(frm){
		frm.trigger("check_quality_checks_link_in_nj_quality_readings")
		// check_empty_quality_check_nj_quality_readings(frm)
		

	},
	set_camera_button(frm){
		frm.add_custom_button(__('<i class="fa fa-camera"></i> Start'), function() {
			frappe.msgprint("Camera");
			// Check if the browser supports the getUserMedia API
				if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
					// Access the user media (camera) and video stream
					navigator.mediaDevices.getUserMedia({ video: true })
						.then(function(stream) {
							// Get the video element from the DOM
							var videoElement = document.getElementById('video');

							// Set the video stream as the source for the video element
							videoElement.srcObject = stream;

							// Play the video stream
							videoElement.play();
						})
						.catch(function(error) {
							console.error('Camera access error:', error);
						});
				} else {
					console.error('getUserMedia API is not supported in this browser.');
				}

		}).addClass('btn-primary');
	},
	scan_barcode(frm){
		frm.trigger('add_nj_quality_readings');
	},
	// scan barcode, fetch item details and set quality reading - code changes done by Anuradha(7-12-23)
	add_nj_quality_readings(frm){
		frappe.call({
			method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.get_barcode_details",
			args:{barcode: frm.doc.scan_barcode, inspection_type: frm.doc.inspection_type},
			callback: function(r) {
				if(r.message){
					let linked_doc = r.message;
					let is_item_and_item_group_added = check_item_group_and_item_added(frm, linked_doc)
					if (!(is_item_and_item_group_added)){
						console.log("check_name1",linked_doc.name)
						if (check_item_already_added(frm, linked_doc)){
							console.log("check_name2",linked_doc.name)
							frappe.confirm(`The item <b>${linked_doc.item_code}</b> already added. you want to continue?`,
								() => {
									// action to perform if Yes is selected
									//console.log("check_name1",linked_doc.name)
									let row_data = {
										item: linked_doc.item_code,
										item_group: linked_doc.item_group,
										quality_check:linked_doc.quality_check,
										part_serial_no:linked_doc.name
									}
									let row = frm.add_child('nj_quality_readings', row_data);

									frm.doc.scan_barcode = null
									frm.refresh_field('nj_quality_readings');
									frm.refresh_field('scan_barcode');
								}, () => {
									// action to perform if No is selected
								});
						}else{
							let row_data = {
								item: linked_doc.item_code,
								item_group: linked_doc.item_group,
								quality_check:linked_doc.quality_check,
								part_serial_no:linked_doc.name
							}
							let row = frm.add_child('nj_quality_readings', row_data);
						}
					}
					
					frm.doc.scan_barcode = null
					frm.refresh_field('nj_quality_readings');
					frm.refresh_field('scan_barcode');

				}else{
					frappe.msgprint({
						title: __('Error'),
						indicator: 'red',
						message: __('The barcode not exist in <b>Serial No</b>. Please check the barcode you entered')
					});
					frm.doc.scan_barcode = null
					frm.refresh_field('scan_barcode');
				}
			}
		});
	}
	
});


const check_item_group_and_item_added = (frm, linked_doc) => {
	console.log(linked_doc)
	for (const nqr of frm.doc.nj_quality_readings){
		if (nqr.item_group == linked_doc.item_group && !Boolean(nqr.item)){
			nqr.item = linked_doc.item_code
			nqr.part_serial_no=linked_doc.name
			frm.refresh_field('nj_quality_readings')
			return true
		}
	}
	return false
}


const check_item_already_added = (frm, linked_doc) => {
	for (const nqr of frm.doc.nj_quality_readings){
		if (nqr.item == linked_doc.item_code){
			return true
		}
	}
	return false
}


function get_itm_code_on_barcode(frm){
 if(frm.doc.name){
    frappe.call({
		method: "frappe.client.get",
		args:{
			doctype: "Serial No",
			filters: {name: frm.doc.barcode}
		},
		callback: function(r) {
			//console.log("### r",r.message)
			frm.set_value("item_code", r.message.item_code);
			// frm.set_value("item_serial_no", r.message.name);
			// frm.set_value("sample_size", "1");
			frm.set_value("item_group",r.message.item_group);
			frm.set_value("item_name",r.message.item_name);
		},
		error: function(r) {
			frm.set_value("item_group", null);
		}
		
	});

     }
 }

function fill_nj_quality_reading_from_serial_or_itm_wizard(frm){
	if(frm.doc.barcode){
			frappe.call({
				method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.fetch_nj_qlty_readings",
				args: {
					'doc':frm.doc
				},
				callback: function(r) {
					
					cur_frm.clear_table("nj_quality_readings")
					cur_frm.refresh_field("nj_quality_readings")
					for (let i = 0; i < r.message.length; i++) {
						var childTable = cur_frm.add_child("nj_quality_readings")
						childTable.item_group = r.message[i].item_group
						childTable.quality_check=r.message[i].quality_check
					}
					cur_frm.refresh_field("nj_quality_readings")
					
				}
			});
  }
}

function add_item_group_and_Quality_check(frm){
	    const Exixting_item_group=[]
         if(frm.doc.item_group && frm.doc.inspection_type){
			if (frm.doc.nj_quality_readings == undefined || frm.doc.nj_quality_readings == null){
				frm.doc.nj_quality_readings = []
			}
            for (const nqr of frm.doc.nj_quality_readings){
				Exixting_item_group.push(nqr.item_group)
				}
				if(Exixting_item_group.includes(frm.doc.item_group)===false){
					var childTable1 = cur_frm.add_child("nj_quality_readings");
					childTable1.item_group=frm.doc.item_group
					frappe.db.get_value('NJ Quality Checks',`${frm.doc.inspection_type}-${frm.doc.item_group}`,'name')
					.then(r => {
					if(r.message.name){
						childTable1.quality_check = r.message.name		
						  }
						})
				}
				
			}
	cur_frm.refresh_fields("nj_quality_readings")
}


function set_quality_checks_as_per_inspection_type(frm){
	
	if(frm.doc.nj_quality_readings == undefined || frm.doc.nj_quality_readings == null){
		frm.doc.nj_quality_readings =[]
	}
	console.log("frm.doc.nj_quality_readings", frm.doc.nj_quality_readings)
	if( frm.doc.inspection_type && frm.doc.bios_serial_number){
		frappe.call({
			method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.get_quality_checks_data",
			args:{
			
				'doc':frm.doc
			},
			callback: function(r) {
				if (r.message.length > 0){
					 console.log("rrrrr",r)
					$.each(r.message, function(i, v) {
						$.each(frm.doc.nj_quality_readings, function(j, qr) {
						if(qr.item_group == v.item_group && v.quality_check != 'None'){
							qr.quality_check = v.quality_check

						}
						});
					});
					refresh_field("nj_quality_readings");
				}
				
				
				
			}
		});
	}

	// for(const i of Nj_Quality_Readings)
	// { 	
	// 	var childTable = cur_frm.add_child("nj_quality_readings")
	// 	childTable.item_group = i.item_group

	// 		frappe.db.get_list('NJ Quality Checks', {
	// 			filters: {
	// 				'item_group':i.item_group,
	// 				'inspection_type':frm.doc.inspection_type,
	// 			},
	// 			fields: ['name'],
	// 			limit: 500,
	// 		}).then(res => {
	// 			console.log('res',res[0].name)
	// 			childTable.quality_check= res[0].name
	// 			cur_frm.refresh_fields("nj_quality_readings")

	// 		});
			//var val = tbl_data_list[0]
			
			
	// 		cur_frm.refresh_fields("nj_quality_readings")
			
    // }
	
}


// function set_abbr(frm){

// var abbreviation= frappe.db.get_value('Inspection Type', frm.doc.inspection_type, 'abbreviation', (values) => {
// 	console.log("values", values)
// 	frm.set_value("abbr",values.abbreviation)
// 	});
	
// }



//  function set_data_inspection_type_data_dynamicaly(frm){
// 	frappe.call({
// 		method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.set_data_inspection_type_data_dynamicaly",
// 		args:{
			
// 		},
// 		callback: function(r) {
// 			frm.set_df_property("inspection_type", "options",r.message);
// 		}
// 	});


//  }
 function check_empty_quality_check_nj_quality_readings(frm){
	$.each(frm.doc.nj_quality_readings, function(i, v) {
		if(v.quality_check == " "){
			frappe.msgprint({title:'Suggestion',
				message:`Quality Checks is not avalible for item group Please Check Nj Quality Readings`
			})
		}
	});

	// for(const i of frm.doc.nj_quality_readings){
	// 	console.log(i)
	// 	if(i.quality_check=== ''){
    //        // frappe.throw(i.item_code)
	// 	   console.log("i.quality_check", i.quality_check)
		//    frappe.throw({title:'Suggestion',
		//           message:`Quality Checks is not Avalible for item group Pls Check Nj Quality Readings`
		// 		})
		   
		// }
	// }
 }



 const set_valuation_rate = (frm) => {
	for (let row of frm.doc.nj_quality_readings){
		get_valuation_rate(frm, row);
	}
 }

 const get_valuation_rate = (frm, row) => {
	if (row.item && row.grade){
		if (row.grade == 'Grade A'){
			const valuation_rate = get_valuation_rate_for_grade_a(frm, row)
		}
	}
 }




 const get_valuation_rate_for_grade_a = (frm, row) => {
	let valuation_rate
	let rate = frappe.call({
		method: "nj_p1_features.nj_p1_features.doctype.nj_quality_inspection.nj_quality_inspection.get_valuation_rate",
		type: "POST",
		args: {doc:frm.doc, row:row},
		async: false,
		callback: function(r) {
			let linked_doc = r.message
			// frappe.msgprint({
			// 	title: __('Notification'),
			// 	indicator: 'green',
			// 	message: __(`Item <b>${row.item}</b> Valuation Rate <b>${linked_doc.valuation_rate}</b><br>
			// 				<b>Grade A</b> rate ${linked_doc.grade_a_rate}<br>
			// 				<b>Grade C</b> rate ${linked_doc.grade_c_rate}<br>
			// 				<b>Grade D</b> rate ${linked_doc.grade_d_rate}
			// 				`)
			// });
		}
	});

	return valuation_rate
	
 }