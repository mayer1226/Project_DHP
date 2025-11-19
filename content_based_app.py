import streamlit as st
import pandas as pd
import pickle

# function cần thiết
def get_recommendations(df, id, cosine_sim, nums=5):
    # Get the index of the bike that matches the bike_id
    matching_indices = df.index[df['id'] == id].tolist()
    if not matching_indices:
        print(f"No motobike found with ID: {id}")
        return pd.DataFrame()  # Return an empty DataFrame if no match
    idx = matching_indices[0]

    # Get the pairwise similarity scores of all bikes with that bike
    sim_scores = list(enumerate(cosine_sim[idx]))

    # Sort the bikes based on the similarity scores
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Get the scores of the nums most similar bikes (Ignoring the bike itself)
    sim_scores = sim_scores[1:nums+1]

    # Get the bike indices
    bike_indices = [i[0] for i in sim_scores]

    # Return the top n most similar bikes as a DataFrame
    return df.iloc[bike_indices]

# Hiển thị đề xuất ra bảng
def display_recommended_bikes(recommended_bikes, cols=5):
    for i in range(0, len(recommended_bikes), cols):
        cols = st.columns(cols)
        for j, col in enumerate(cols):
            if i + j < len(recommended_bikes):
                bike = recommended_bikes.iloc[i + j]
                with col:   
                    st.write(bike['title'])                    
                    expander = st.expander(f"Description")
                    bike_description = bike['description']
                    truncated_description = ' '.join(bike_description.split()[:100]) + '...'
                    expander.write(truncated_description)
                    expander.markdown("Nhấn vào mũi tên để đóng hộp text này.")           

# Đọc dữ liệu xe máy từ file excel
df_bikes = pd.read_excel('mau_xe_may.xlsx', engine='openpyxl')
# Lấy 10 xe máy
random_bikes = df_bikes.head(n=10)
# print(random_bikes)

st.session_state.random_bikes = random_bikes

# Open and read file to cosine_sim_new
with open('xe_cosine_sim_18112025.pkl', 'rb') as f:
    cosine_sim_new = pickle.load(f)

###### Giao diện Streamlit ######
### cho version cũ
st.image('xe_may_cu.jpg', use_column_width=True)
### cho version mới
# st.image("xe_may_cu.jpg", use_container_width=True)


# Kiểm tra xem 'selected_bike_id' đã có trong session_state hay chưa
if 'selected_bike_id' not in st.session_state:
    # Nếu chưa có, thiết lập giá trị mặc định là None hoặc ID khách sạn đầu tiên
    st.session_state.selected_bike_id = None

# Theo cách cho người dùng chọn khách sạn từ dropdown
# Tạo một tuple cho mỗi khách sạn, trong đó phần tử đầu là tên và phần tử thứ hai là ID
bike_options = [(row['title'], row['id']) for index, row in st.session_state.random_bikes.iterrows()]
# st.session_state.random_bikes
# Tạo một dropdown với options là các tuple này
selected_bike = st.selectbox(
    "Chọn xe may bạn quan tâm:",
    options=bike_options,
    format_func=lambda x: x[0]  # Hiển thị tên xe máy
)
# Display the selected bike
# st.write("Bạn đã chọn:", selected_bike)

# Cập nhật session_state dựa trên lựa chọn hiện tại
st.session_state.selected_bike_id = selected_bike[1]

if st.session_state.selected_bike_id:
    st.write("bike_ID: ", st.session_state.selected_bike_id)
    # Hiển thị thông tin xe máy được chọn
    selected_bike = df_bikes[df_bikes['id'] == st.session_state.selected_bike_id]

    if not selected_bike.empty:
        st.write('#### Bạn vừa chọn:')
        st.write('### ', selected_bike['title'].values[0])

        bike_description = selected_bike['description'].values[0]
        truncated_description = ' '.join(bike_description.split()[:100])
        st.write('##### Thông tin:')
        st.write(truncated_description, '...')

        st.write('##### Các xe máy khác bạn cũng có thể quan tâm:')
        recommendations = get_recommendations(df_bikes, st.session_state.selected_bike_id, cosine_sim=cosine_sim_new, nums=3) 
        display_recommended_bikes(recommendations, cols=3)
    else:
        st.write(f"Không tìm thấy xe máy với ID: {st.session_state.selected_bike_id}")
