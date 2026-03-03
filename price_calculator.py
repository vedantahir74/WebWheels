"""
Vehicle Fair Price Calculator - ADJUSTED VERSION
Rule-based pricing system with HIGHER prices
Adjustable depreciation and deduction rates
"""

from datetime import datetime

class price_calculator:
    """Calculate vehicle resale price using adjustable rule-based formula"""
    BRAND_MULTIPLIERS = {

        
        "Toyota": 1.1,
        "Maruti Suzuki": 1.1,
        "Hyundai": 1,

        # Strong Brands
        "Honda": 1,
        "Tata Motors": 0.95,
        "Mahindra": 0.95,
        "Kia": 0.92,

        # Premium Segment (Luxury brands depreciate faster but still strong)
        "Mercedes-Benz": 0.95,
        "BMW": 0.94,
        "Audi": 0.92,
        "Volvo": 0.91,
        "Land Rover": 0.90,

        # Average Brands
        "MG": 0.90,
        "Skoda": 0.88,
        "Volkswagen": 0.87,

        # Lower Resale Brands
        "Renault": 0.85,
        "Nissan": 0.83,
        "Ford": 0.80,
        "Chevrolet": 0.75
    }
    # Base prices for different brands and models (in INR)
    BASE_PRICES  = {

    # ------------------ MARUTI SUZUKI ------------------
    "Maruti Suzuki": {
        "Alto": {"STD": 360000, "LXi": 395000, "VXi": 430000},
        "Alto K10": {"LXi": 400000, "VXi": 450000, "VXi+": 495000},
        "S-Presso": {"STD": 420000, "LXi": 460000, "VXi": 510000, "VXi+": 560000},
        "Celerio": {"LXi": 540000, "VXi": 600000, "ZXi": 660000, "ZXi+": 720000},
        "Wagon R": {"LXi": 550000, "VXi": 620000, "ZXi": 700000, "ZXi+": 780000},
        "Ignis": {"Sigma": 580000, "Delta": 650000, "Zeta": 720000, "Alpha": 790000},
        "Swift": {"LXi": 650000, "VXi": 720000, "ZXi": 800000, "ZXi+": 880000},
        "Dzire": {"LXi": 670000, "VXi": 740000, "ZXi": 820000, "ZXi+": 900000},
        "Baleno": {"Sigma": 660000, "Delta": 730000, "Zeta": 800000, "Alpha": 870000},
        "Ciaz": {"Sigma": 930000, "Delta": 1000000, "Zeta": 1100000, "Alpha": 1200000},
        "Ertiga": {"LXi": 890000, "VXi": 980000, "ZXi": 1080000, "ZXi+": 1180000},
        "XL6": {"Zeta": 1150000, "Alpha": 1250000, "Alpha+": 1350000},
        "Brezza": {"LXi": 840000, "VXi": 950000, "ZXi": 1100000, "ZXi+": 1300000},
        "Grand Vitara": {"Sigma": 1090000, "Delta": 1250000, "Zeta": 1450000, "Alpha": 1700000},
        "Jimny": {"Zeta": 1250000, "Alpha": 1400000},
        "Fronx": {"Sigma": 750000, "Delta": 850000, "Zeta": 950000, "Alpha": 1050000},
        "Invicto": {"Zeta+": 2400000, "Alpha+": 2600000, "Alpha+ Hybrid": 2850000}
    },

    # ------------------ HYUNDAI ------------------
    "Hyundai": {

        "Santro": {
            "Era": 440000,"Magna": 500000,"Sportz": 560000
        },

        "Grand i10 Nios": {
            "Era": 580000,
            "Magna": 650000,
            "Sportz": 720000,
            "Asta": 800000
        },

        "i20": {
            "Magna": 720000,
            "Sportz": 800000,
            "Asta": 880000,
            "Asta(O)": 950000
        },

        "i20 N Line": {
            "N6": 1100000,
            "N8": 1180000
        },

        "Aura": {
            "E": 640000,
            "S": 700000,
            "SX": 780000,
            "SX(O)": 860000
        },

        "Verna": {
            "EX": 1150000,
            "S": 1250000,
            "SX": 1450000,
            "SX(O)": 1650000
        },

        "Creta": {
            "E": 1100000,
            "S": 1250000,
            "SX": 1450000,
            "SX(O)": 1700000
        },

        "Venue": {
            "E": 800000,
            "S": 880000,
            "SX": 980000,
            "SX(O)": 1100000
        },

        "Exter": {
            "EX": 900000,
            "S": 980000,
            "SX": 1080000,
            "SX(O)": 1180000
        },

        "Alcazar": {
            "Prestige": 1700000,
            "Platinum": 1900000,
            "Signature": 2100000
        },

        "Tucson": {
            "Platinum": 2900000,
            "Signature": 3200000
        },

        "Kona Electric": {
            "Premium": 2400000,
            "Premium Dual Tone": 2480000
        },

        "Ioniq 5": {
            "RWD": 4600000,
            "AWD": 5000000
        }
    },

        # ------------------ TATA ------------------
    "Tata Motors":  {

        "Tiago": {
            "XE": 550000,
            "XT": 620000,
            "XZ": 680000,
            "XZ+": 730000
        },

        "Tigor": {
            "XE": 600000,
            "XT": 680000,
            "XZ": 750000,
            "XZ+": 820000
        },

        "Altroz": {
            "XE": 650000,
            "XM": 720000,
            "XZ": 820000,
            "XZ+": 900000
        },

        "Punch": {
            "Pure": 610000,
            "Adventure": 680000,
            "Creative": 750000,
            "Accomplished": 820000
        },

        "Nexon": {
            "Smart": 800000,
            "Pure": 950000,
            "Creative": 1100000,
            "Fearless": 1300000
        },

        "Harrier": {
            "Smart": 1550000,
            "Pure": 1700000,
            "Adventure": 1900000,
            "Fearless": 2200000
        },

        "Safari": {
            "Smart": 1650000,
            "Pure": 1800000,
            "Adventure": 2000000,
            "Fearless": 2300000
        },

        "Nexon EV": {
            "Creative": 1450000,
            "Fearless": 1650000,
            "Empowered": 1800000
        },

        "Tiago EV": {
            "XE": 800000,
            "XT": 900000,
            "XZ+": 1050000
        },

        "Tigor EV": {
            "XE": 1200000,
            "XT": 1280000,
            "XZ+": 1380000
        }
    },
    # ------------------ MAHINDRA ------------------
    "Mahindra":  {

        "Bolero": {
            "B4": 980000,
            "B6": 1050000,
            "B6(O)": 1120000
        },

        "Scorpio": {
            "S": 1300000,
            "S11": 1650000
        },

        "Scorpio-N": {
            "Z2": 1350000,
            "Z4": 1550000,
            "Z6": 1750000,
            "Z8": 2000000,
            "Z8L": 2300000
        },

        "XUV300": {
            "W4": 850000,
            "W6": 1000000,
            "W8": 1200000
        },

        "XUV400": {
            "EC": 1500000,
            "EL": 1700000
        },

        "XUV700": {
            "MX": 1400000,
            "AX3": 1600000,
            "AX5": 1800000,
            "AX7": 2100000,
            "AX7L": 2400000
        },

        "Thar": {
            "AX": 1100000,
            "LX": 1250000,
            "LX 4x4": 1500000
        },

        "Bolero Neo": {
            "N4": 1000000,
            "N8": 1100000,
            "N10": 1200000
        },

        "Marazzo": {
            "M2": 1450000,
            "M4": 1550000,
            "M6": 1700000
        },

        "KUV100": {
            "K2": 600000,
            "K4": 650000,
            "K6": 720000
        }
    },


    # ------------------ TOYOTA ------------------
    "Toyota": {

        "Glanza": {
            "E": 670000,
            "S": 750000,
            "G": 850000,
            "V": 950000
        },

        "Urban Cruiser Hyryder": {
            "E": 1090000,
            "S": 1250000,
            "G": 1500000,
            "V": 1800000
        },

        "Innova Crysta": {
            "GX": 1900000,
            "VX": 2100000,
            "ZX": 2350000
        },

        "Innova Hycross": {
            "G": 1850000,
            "GX": 2050000,
            "VX": 2300000,
            "ZX": 2800000
        },

        "Fortuner": {
            "4x2": 3300000,
            "4x4": 3700000,
            "Legender": 4200000
        },

        "Legender": {
            "4x2 AT": 4300000,
            "4x4 AT": 4600000
        },

        "Camry": {
            "Hybrid": 4600000
        },

        "Vellfire": {
            "Hi": 9500000,
            "VIP": 10500000
        }
    },

    "Honda" : {

        "Amaze": {
            "E": 750000,
            "S": 820000,
            "VX": 900000
        },

        "Jazz": {
            "V": 820000,
            "VX": 900000,
            "ZX": 980000
        },

        "City": {
            "SV": 1150000,
            "V": 1250000,
            "VX": 1400000,
            "ZX": 1550000
        },

        "City Hybrid": {
            "V": 1900000,
            "ZX": 2050000
        },

        "WR-V": {
            "S": 900000,
            "VX": 1050000
        },

        "Elevate": {
            "SV": 1100000,
            "V": 1250000,
            "VX": 1450000,
            "ZX": 1600000
        }
    },
    "Kia" :{

        "Seltos": {
            "HTE": 1090000,
            "HTK": 1250000,
            "HTX": 1500000,
            "GTX+": 1850000,
            "X-Line": 2000000
        },

        "Sonet": {
            "HTE": 800000,
            "HTK": 900000,
            "HTX": 1050000,
            "GTX+": 1350000
        },

        "Carens": {
            "Premium": 1050000,
            "Prestige": 1250000,
            "Luxury": 1550000,
            "Luxury+": 1800000
        },

        "EV6": {
            "GT Line": 6000000,
            "GT": 6500000
        },

        "Carnival": {
            "Premium": 3000000,
            "Limousine": 3500000
        }
    },


    # ------------------ LUXURY BRANDS ------------------
    "Mercedes-Benz":  {

        "A-Class": {
            "A200": 4500000,
            "A220d": 4800000
        },

        "C-Class": {
            "C200": 6000000,
            "C220d": 6300000
        },

        "E-Class": {
            "E200": 7500000,
            "E350d": 8800000
        },

        "S-Class": {
            "S350d": 17000000,
            "S450": 18000000
        },

        "GLA": {
            "200": 4800000,
            "220d": 5200000
        },

        "GLC": {
            "300": 7000000,
            "220d": 7300000
        },

        "GLE": {
            "300d": 9500000,
            "450": 10500000
        },

        "GLS": {
            "400d": 13500000,
            "Maybach": 30000000
        }
    },


    "BMW":  {

        "2 Series": {
            "220i": 4300000,
            "220d": 4500000
        },

        "3 Series": {
            "330i": 7200000,
            "320d": 7500000
        },

        "5 Series": {
            "530i": 6800000,
            "520d": 7200000
        },

        "7 Series": {
            "740i": 17000000,
            "740d": 17500000
        },

        "X1": {
            "sDrive18i": 4900000,
            "sDrive18d": 5200000
        },

        "X3": {
            "xDrive30i": 7000000,
            "xDrive20d": 7400000
        },

        "X5": {
            "xDrive40i": 9500000,
            "xDrive30d": 9800000
        },

        "X7": {
            "xDrive40i": 12500000,
            "xDrive40d": 13000000
        }
    },

    "Audi":{

        "A3": {
            "Premium": 3600000,
            "Technology": 3900000
        },

        "A4": {
            "Premium": 4600000,
            "Premium Plus": 5000000
        },

        "A6": {
            "Premium": 6000000,
            "Technology": 6500000
        },

        "A8": {
            "L": 16000000,
            "L Technology": 17000000
        },

        "Q3": {
            "Premium": 4500000,
            "Technology": 5000000
        },

        "Q5": {
            "Premium Plus": 6500000,
            "Technology": 7000000
        },

        "Q7": {
            "Premium Plus": 8500000,
            "Technology": 9000000
        },

        "Q8": {
            "Celebration": 10500000,
            "Technology": 11500000
        }
    },


    # ================== MG ==================
    "MG": {
        "Hector": {"Style": 1450000, "Shine": 1600000, "Smart": 1800000, "Sharp": 2100000},
        "Astor": {"Sprint": 1050000, "Shine": 1200000, "Sharp": 1400000, "Savvy": 1650000},
        "Gloster": {"Super": 3800000, "Sharp": 4100000, "Savvy": 4500000},
        "ZS EV": {"Excite": 2300000, "Exclusive": 2600000},
        "Comet EV": {"Pace": 700000, "Play": 800000, "Plush": 900000}
    },

    # ================== RENAULT ==================
    "Renault": {
        "Kwid": {"RXE": 470000, "RXL": 520000, "RXT": 580000},
        "Triber": {"RXE": 620000, "RXL": 690000, "RXT": 760000},
        "Kiger": {"RXE": 630000, "RXL": 720000, "RXT": 820000, "RXZ": 950000}
    },

    # ================== NISSAN ==================
    "Nissan": {
        "Magnite": {"XE": 600000, "XL": 680000, "XV": 820000, "XV Premium": 1000000},
        "Kicks": {"XL": 950000, "XV": 1100000, "XV Premium": 1300000}
    },

    # ================== VOLKSWAGEN ==================
    "Volkswagen": {
        "Polo": {"Trendline": 700000, "Comfortline": 780000, "Highline": 860000, "GT": 950000},
        "Vento": {"Trendline": 900000, "Comfortline": 1000000, "Highline": 1100000},
        "Taigun": {"Comfortline": 1150000, "Highline": 1400000, "GT": 1750000},
        "Virtus": {"Comfortline": 1100000, "Highline": 1350000, "GT": 1700000},
        "Tiguan": {"Elegance": 3500000}
    },

    # ================== SKODA ==================
    "Skoda": {
        "Kushaq": {"Active": 1100000, "Ambition": 1300000, "Style": 1550000},
        "Slavia": {"Active": 1050000, "Ambition": 1250000, "Style": 1500000},
        "Kodiaq": {"Style": 3800000, "L&K": 4200000},
        "Superb": {"Sportline": 3500000, "L&K": 3800000}
    },

    # ================== FORD ==================
    "Ford": {
        "EcoSport": {"Ambiente": 800000, "Trend": 900000, "Titanium": 1050000},
        "Endeavour": {"Titanium": 3000000, "Sport": 3300000},
        "Figo": {"Ambiente": 550000, "Trend": 620000, "Titanium": 700000},
        "Aspire": {"Ambiente": 650000, "Trend": 720000, "Titanium": 800000},
        "Freestyle": {"Ambiente": 750000, "Trend": 820000, "Titanium": 900000}
    },

    # ================== JEEP ==================
    "Jeep": {
        "Compass": {"Sport": 2000000, "Longitude": 2300000, "Limited": 2600000},
        "Meridian": {"Limited": 3100000, "Limited(O)": 3300000, "Overland": 3600000},
        "Wrangler": {"Unlimited": 6200000, "Rubicon": 6800000},
        "Grand Cherokee": {"Limited": 8000000, "Summit": 8500000}
    },

    # ================== FORCE MOTORS ==================
    "Force Motors": {
        "Gurkha": {"3 Door": 1600000, "5 Door": 1800000},
        "One": {"STD": 1200000}
    },

# ================== ISUZU ==================
    "Isuzu": {
        "D-Max V-Cross": {"Z": 2100000, "Z Prestige": 2400000},
        "MU-X": {"4x2": 3500000, "4x4": 3800000}
    }

}

    ANNUAL_DEPRECIATION_RATE = 0.07
    KM_DEDUCTION_PER_KM = 1.4
    FUEL_ADJUSTMENTS = {
        "Petrol": 0,
        "Diesel": 15000,
        "CNG": -10000,
        "Electric": 30000
    }
    TRANSMISSION_ADJUSTMENTS = {
        "Manual": 0,
        "Automatic": 20000
    }
    ENGINE_CAPACITY_THRESHOLDS = {
        'above_1500cc': 20000,
        'below_1000cc': -15000
    }
    MILEAGE_ADJUSTMENTS = {
        'above_18kmpl': 15000,
        'below_12kmpl': -15000
    }
    BODY_TYPE_ADJUSTMENTS = {
        'SUV': 30000,
        'Sedan': 20000,
        'Hatchback': 0,
        'MPV': 25000,
        'Coupe': 15000,
        'Convertible': 20000
    }

    FEATURE_BONUS_PER_ITEM = 7500  
    
    # Minimum price floor (in INR)
    MINIMUM_PRICE = 100000 
    
    def __init__(self):
        """Initialize the calculator"""
        self.current_year = datetime.now().year
        self.calculations = {}
    
    def calculate_fair_price(self, vehicle_data):
        """
        Calculate fair resale price for a vehicle
        
        Args:
            vehicle_data (dict): Vehicle details
        
        Returns:
            dict: Calculated price and breakdown
        """
        try:
            # Reset calculations
            self.calculations = {}
            
            # Step 1: Get base price
            base_price = self._get_base_price(
                vehicle_data.get('brand'),
                vehicle_data.get('model'),
                vehicle_data.get('variant')
            )
            self.calculations['base_price'] = base_price
            
            # Step 2: Apply year depreciation
            manufacturing_year = int(vehicle_data.get('manufacturing_year', self.current_year))
            year_depreciation = self._apply_year_depreciation(base_price, manufacturing_year)
            self.calculations['year_depreciation'] = year_depreciation
            
            # Step 3: Apply kilometer deduction
            kilometers_driven = int(vehicle_data.get('kilometers_driven', 0))
            kilometer_deduction = self._apply_kilometer_deduction(kilometers_driven)
            self.calculations['kilometer_deduction'] = kilometer_deduction
            
            # Step 4: Apply fuel type adjustment
            fuel_type = vehicle_data.get('fuel_type', 'Petrol')
            fuel_adjustment = self._apply_fuel_type_adjustment(fuel_type)
            self.calculations['fuel_adjustment'] = fuel_adjustment
            
            # Step 5: Apply transmission adjustment
            transmission = vehicle_data.get('transmission', 'Manual')
            transmission_adjustment = self._apply_transmission_adjustment(transmission)
            self.calculations['transmission_adjustment'] = transmission_adjustment
            
            # Step 6: Apply engine capacity adjustment
            engine_capacity = int(vehicle_data.get('engine_capacity', 1200))
            engine_adjustment = self._apply_engine_capacity_adjustment(engine_capacity)
            self.calculations['engine_adjustment'] = engine_adjustment
            
            # Step 7: Apply mileage adjustment
            mileage = float(vehicle_data.get('mileage', 15))
            mileage_adjustment = self._apply_mileage_adjustment(mileage)
            self.calculations['mileage_adjustment'] = mileage_adjustment
            
            # Step 8: Apply body type adjustment
            body_type = vehicle_data.get('body_type', 'Hatchback')
            body_type_adjustment = self._apply_body_type_adjustment(body_type)
            self.calculations['body_type_adjustment'] = body_type_adjustment
            
            # Step 9: Apply feature bonus
            features = vehicle_data.get('features', [])
            if isinstance(features, str):
                features = [f.strip() for f in features.split(',') if f.strip()]
            feature_bonus = self._apply_feature_bonus(features)
            self.calculations['feature_bonus'] = feature_bonus
            self.calculations['features_count'] = len(features)
            
            # Step 10: Calculate final price
            price_before_brand = (
                base_price
                - year_depreciation
                - kilometer_deduction
                + fuel_adjustment
                + transmission_adjustment
                + engine_adjustment
                + mileage_adjustment
                + body_type_adjustment
                + feature_bonus
            )

            # Step 10: Apply Brand Multiplier
            brand = vehicle_data.get('brand')
            final_price, brand_multiplier = self._apply_brand_multiplier(brand, price_before_brand)

            self.calculations['brand_multiplier'] = brand_multiplier
            self.calculations['brand_adjustment'] = final_price - price_before_brand

            
            # Ensure minimum price
            final_price = max(final_price, self.MINIMUM_PRICE)
            
            # Round to nearest 10,000
            final_price = round(final_price / 10000) * 10000
            
            self.calculations['final_price'] = final_price
            
            # Calculate vehicle age
            vehicle_age = self.current_year - manufacturing_year
            self.calculations['vehicle_age'] = vehicle_age
            
            return {
                'success': True,
                'final_price': int(final_price),
                'base_price': int(base_price),
                'vehicle_age': vehicle_age,
                'breakdown': self._get_breakdown(vehicle_data),
                'adjustments': {
                    'year_depreciation': -int(year_depreciation),
                    'kilometer_deduction': -int(kilometer_deduction),
                    'fuel_adjustment': int(fuel_adjustment),
                    'transmission_adjustment': int(transmission_adjustment),
                    'engine_adjustment': int(engine_adjustment),
                    'mileage_adjustment': int(mileage_adjustment),
                    'body_type_adjustment': int(body_type_adjustment),
                    'feature_bonus': int(feature_bonus),
                }
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'final_price': 0,
            }
    
    def _get_base_price(self, brand, model, variant=None):
        brand = str(brand).strip()
        model = str(model).strip()

        try:
            # If variant exists
            if variant:
                variant = str(variant).strip()
                return self.BASE_PRICES[brand][model][variant]

            # If no variant but nested dict exists
            model_data = self.BASE_PRICES[brand][model]
            if isinstance(model_data, dict):
                # Return first variant price
                return list(model_data.values())[0]

            return model_data

        except KeyError:
            print(f"Warning: {brand} {model} not found. Using default ₹1,000,000")
            return 1000000

    
    def _apply_year_depreciation(self, base_price, manufacturing_year):
        """Apply depreciation based on vehicle age"""
        vehicle_age = max(0, self.current_year - manufacturing_year)
        depreciation = (base_price * self.ANNUAL_DEPRECIATION_RATE) * vehicle_age
        return depreciation
    
    def _apply_kilometer_deduction(self, kilometers_driven):
        """Deduct based on kilometers driven"""
        return kilometers_driven * self.KM_DEDUCTION_PER_KM
    
    def _apply_fuel_type_adjustment(self, fuel_type):
        """Apply fuel type adjustment"""
        fuel_type = str(fuel_type).strip().title() if fuel_type else 'Petrol'
        return self.FUEL_ADJUSTMENTS.get(fuel_type, 0)
    
    def _apply_transmission_adjustment(self, transmission):
        """Apply transmission adjustment"""
        transmission = str(transmission).strip().title() if transmission else 'Manual'
        return self.TRANSMISSION_ADJUSTMENTS.get(transmission, 0)
    
    def _apply_engine_capacity_adjustment(self, engine_capacity):
        """Apply engine capacity adjustment"""
        engine_capacity = int(engine_capacity) if engine_capacity else 1200
        
        if engine_capacity > 1500:
            return self.ENGINE_CAPACITY_THRESHOLDS['above_1500cc']
        elif engine_capacity < 1000:
            return self.ENGINE_CAPACITY_THRESHOLDS['below_1000cc']
        else:
            return 0
    
    def _apply_mileage_adjustment(self, mileage):
        """Apply mileage adjustment"""
        mileage = float(mileage) if mileage else 15
        
        if mileage > 18:
            return self.MILEAGE_ADJUSTMENTS['above_18kmpl']
        elif mileage < 12:
            return self.MILEAGE_ADJUSTMENTS['below_12kmpl']
        else:
            return 0
    
    def _apply_body_type_adjustment(self, body_type):
        """Apply body type adjustment"""
        body_type = str(body_type).strip().title() if body_type else 'Hatchback'
        return self.BODY_TYPE_ADJUSTMENTS.get(body_type, 0)
    
    def _apply_feature_bonus(self, features):
        """Apply feature bonus"""
        if isinstance(features, str):
            features = [f.strip() for f in features.split(',') if f.strip()]
        elif not isinstance(features, list):
            features = []
        
        valid_features = [f for f in features if f and len(str(f).strip()) > 0]
        bonus = len(valid_features) * self.FEATURE_BONUS_PER_ITEM
        return bonus
    def _apply_brand_multiplier(self, brand, price_after_adjustments):
        """Apply brand value multiplier"""
        brand = str(brand).strip()

        multiplier = self.BRAND_MULTIPLIERS.get(brand, 0.90)  # default average brand

        adjusted_price = price_after_adjustments * multiplier

        return adjusted_price, multiplier

    def _get_breakdown(self, vehicle_data):
        """Generate breakdown dictionary"""
        breakdown = {
            'Base Price': f"₹{self.calculations['base_price']:,.0f}",
            'Year Depreciation': f"-₹{self.calculations['year_depreciation']:,.0f}",
            'Kilometer Deduction': f"-₹{self.calculations['kilometer_deduction']:,.0f}",
            'Fuel Type Adjustment': f"+₹{self.calculations['fuel_adjustment']:,.0f}" if self.calculations['fuel_adjustment'] >= 0 else f"-₹{abs(self.calculations['fuel_adjustment']):,.0f}",
            'Transmission Adjustment': f"+₹{self.calculations['transmission_adjustment']:,.0f}" if self.calculations['transmission_adjustment'] >= 0 else f"-₹{abs(self.calculations['transmission_adjustment']):,.0f}",
            'Engine Capacity Adjustment': f"+₹{self.calculations['engine_adjustment']:,.0f}" if self.calculations['engine_adjustment'] >= 0 else f"-₹{abs(self.calculations['engine_adjustment']):,.0f}",
            'Mileage Adjustment': f"+₹{self.calculations['mileage_adjustment']:,.0f}" if self.calculations['mileage_adjustment'] >= 0 else f"-₹{abs(self.calculations['mileage_adjustment']):,.0f}",
            'Body Type Adjustment': f"+₹{self.calculations['body_type_adjustment']:,.0f}" if self.calculations['body_type_adjustment'] >= 0 else f"-₹{abs(self.calculations['body_type_adjustment']):,.0f}",
            'Brand Value Multiplier': f"x {self.calculations.get('brand_multiplier', 1.0)}",
            'Brand Adjustment': f"+₹{self.calculations.get('brand_adjustment', 0):,.0f}" if self.calculations.get('brand_adjustment', 0) >= 0 else f"-₹{abs(self.calculations.get('brand_adjustment', 0)):,.0f}",
            f"Feature Bonus ({self.calculations['features_count']} features)": f"+₹{self.calculations['feature_bonus']:,.0f}",
            '': '──────────────────────────',
            'Final Fair Price': f"₹{self.calculations['final_price']:,.0f}",
        }
        return breakdown


def calculate_fair_price(vehicle_data):
    """Main function to calculate fair vehicle resale price"""
    calculator = price_calculator()
    return calculator.calculate_fair_price(vehicle_data)