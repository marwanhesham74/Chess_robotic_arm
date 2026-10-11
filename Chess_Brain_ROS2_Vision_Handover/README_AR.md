# Chess Brain — التسليم النهائي للـ ROS 2 + Computer Vision

## إحنا بنسلّم إيه؟

دي **باكيدج واحدة** فيها منطق الشطرنج (Stockfish + python-chess)، وحلقة إدارة الأدوار، وواجهة جاهزة لتبادل JSON مع ROS 2 Jazzy والكاميرات.

**مش بنعمل تدريب Stockfish**، ومش محتاجين ملف `games.csv.zip`. المحرك نفسه بيختار النقلات. الباكيدج بتجهّز النقلات للتنفيذ وتتأكد من البورد قبل ما تعتمدها.

> تنبيه: ده إصدار **Integration Handover v1.0**، مش شهادة إن الأذرع الفعلية آمنة أو إن كاميرا حقيقية اتجرّبت. تحتاجون اختبار ROS 2 Jazzy وVision/Hardware قبل التشغيل الفيزيائي.

## كل جزء مسؤول عن إيه؟

- **Computer Vision Team:** يحدد كل مربع على بورد 8×8 ونوع الحجر/لونه أو فاضي، ويرسل 64 خلية مع الـconfidence والتوقيت، والـorientation. الكاميرا المرجعية ثابتة فوق البورد.
- **Chess Brain (الجزء ده):** يحتفظ ببورد واحدة صحيحة، يسأل Stockfish عن النقلة، يرجع خطّة Pick/Place منطقية، يستنى تأكيد الروبوت والكاميرا قبل تحديث اللعبة.
- **ROS / Robotics Team:** يستقبل الخطة، يحول مربعات الشطرنج لإحداثيات الروبوت (TF2/Calibration)، يعمل IK/Trajectory/Gripper/Collision Checking ويجهز الـcapture bin والـpromotion pieces، ويرسل Ack بعد انتهاء الحركة ورجوع الذراع لوضع آمن.
- **Safety Coordinator:** يمنع اصطدام الأذرع؛ لا يعتمد على هذا البرنامج كبديل لإيقاف الطوارئ أو الـinterlock.

## تركيب الباكيدج محليًا على Ubuntu 24.04

```bash
sudo apt update
sudo apt install stockfish python3-venv
cd Chess_Brain_ROS2_Vision_Handover
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Stockfish غالبًا في `/usr/games/stockfish`، ولو مش موجود حدّد `STOCKFISH_PATH` بمساره.

### 1 — الاختبارات (بدون Stockfish)

```bash
python -m unittest discover -s tests -v
```

الاختبارات تستخدم لاعب افتراضي deterministic، وهدفها التحقق من قواعد الشطرنج وواجهة التأكيد. تحتاج مكتبة `chess` فقط.

### 2 — تجربة Stockfish ضد Stockfish

```bash
python -m chess_brain_handover.selfplay --white strong --black medium --max-plies 80 --output results/demo
```

تنتج `moves.csv` و`summary.json`. **دي Self-play مع Fake Camera/Fake Robot للشرح والاختبار فقط**. وصول حد النقلات مش تعادل.

### 3 — عرض Input كامل للكاميرا

```bash
python examples/make_vision_json.py
```

هيطبع Example JSON فيه `cells` عددها 64، والمربعات الفاضية بتتاخد بعلامة `.`.

### 4 — تجربة استخدام الكود مباشرة

```bash
python examples/python_integration.py
```

## تشغيلها من ROS 2 Jazzy

**مهم:** دي `ament_python` ROS 2 package، مش مجرد Python script. استخدم بيئة بايثون فيها `chess` و`rclpy`، وما تخلطش مسارات Python.

طريقة مقترحة (لو ROS 2 Jazzy مُثبت):

```bash
source /opt/ros/jazzy/setup.bash
python3 -m venv --system-site-packages ~/chess_ros_venv
source ~/chess_ros_venv/bin/activate
python -m pip install chess colcon-common-extensions
mkdir -p ~/chess_ws/src
cp -r Chess_Brain_ROS2_Vision_Handover ~/chess_ws/src/chess_brain_handover
cd ~/chess_ws
colcon build --symlink-install --packages-select chess_brain_handover
source install/setup.bash
ros2 launch chess_brain_handover chess_brain.launch.py engine_path:=/usr/games/stockfish
```

لو عندك `colcon` مُثبت بالفعل من apt، مش ضروري تثبت `colcon-common-extensions` بالـpip. راجع إعدادات بيئة Python لو `rclpy` مش ظاهر.

الـNode **مش بيصدر حركة تلقائيًا عند التشغيل**. لازم يوصله أولًا بورد سليمة ومتزامنة، وبعدها `safety_ready=True` من كود السلامة، وبعدين أمر `next`.

**شوف كمان** `docs/ROS2_QUICKSTART.md` و`reference/board_coordinates_64.csv` و`reference/vision_64cells_TEMPLATE.json` (عدّل توقيت الـTemplate قبل الإرسال).

**التفاصيل المهمة جدًا في** `docs/INTEGRATION_CONTRACT.md`: أسماء الـTopics، أمثلة JSON، ترتيب الإشارات، Row/Column، حالات الخطأ.

## المعنى ببساطة

1. الكاميرا تبعت صورة محولة إلى وصف **كل الـ64 مربع**.
2. نعمل `sync` مع البورد الحقيقية.
3. كود السلامة يرسل إنه جاهز؛ حد يطلب `next`.
4. Stockfish يقترح نقلة، والـGameController يعمل `MovePlan` مع `plan_id` مميز.
5. ROS/Robotics يحرك الحجر ويؤكد التنفيذ وعودة الذراع لوضع آمن، مع نفس `plan_id`.
6. الكاميرا تصور البورد بعد التنفيذ وتبعت قراءة جديدة.
7. لو القراءة تطابق الوضع المتوقع: نحدث الـFEN ويتنقل الدور. لو فيه اختلاف: **ما بنكملش تلقائيًا**.

## أنواع الحركات اللي متغطية

- Normal move: قطعة تنتقل من مربع لمربع.
- Capture: إزالة قطعة الخصم أولًا لمنطقة قطع مأخوذة (المكان نفسه يحدده فريق الروبوت).
- Castling: تحريك الملك والقلعة بأمرين منطقيين.
- En passant: إزالة العسكري من مربعه الأصلي المختلف عن مربع وصول المهاجم.
- Promotion: نقل العسكري ثم استبداله بقطعة متوفرة فعلًا في المكان المخصص (فريق الروبوت مسؤول عن المخزون والتعامل الفيزيائي).

## حدود التسليم بوضوح

- لا توجد صور ولا YOLO ولا تدريب Vision هنا.
- لا توجد IK/TF2/MoveIt أو وصلات محركات أو مستشعرات فعلية داخل الباكيدج.
- ROS 2 adapter يستخدم `std_msgs/String` JSON كـ**عقد أولي بين الفرق**؛ في النسخة النهائية للمشروع يُفضل تحويله إلى custom typed interfaces وROS Actions لتأكيد التنفيذ والـtimeouts.
- حقل `safety_ready` إشارة من الـcoordinator **مش بديل لأمان حقيقي**، ورسالته قد لا تكون حديثة أو موثوقة دون ضمانات من طبقة الأجهزة.
- طوابع الوقت لازم تكون متزامنة بين الكاميرات والكمبيوتر؛ قراءة أقدم من Ack مرفوضة.
- الكود لا يعيد محاولة Pick/Place تلقائيًا في حالة الخطأ.
- لا توجد استعادة آلية كاملة بعد إعادة تشغيل النظام. استعادة حالة المباراة والجهاز تحتاج إجراء إعادة تحقق صريح من المشغّل.

## قبل التسليم للـIntegration Team

1. نفّذ الـUnit Tests.
2. نفّذ Demo Stockfish الحقيقي.
3. اتفقوا على اتجاه البورد `a8_top_left`، ونوع قطع FEN، ووجود الـ64 مربع، وتوقيت الكاميرات.
4. فريق الروبوت مسؤول عن مكان القطع المأسورة وقطع الترقية، وAck أمن لكل حركة.
5. جرّبوا Hardware-in-the-loop في Gazebo ثم على سرعة قليلة في مكان آمن قبل اللعب الحقيقي.

راجع `docs/VALIDATION_STATUS.md` علشان تميّز النتائج المتحققة فعليًا من اللي لسه محتاجة اختبار.
