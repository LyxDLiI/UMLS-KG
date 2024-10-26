from neo4j import GraphDatabase
import json

# 连接到Neo4j数据库的参数
NEO4J_URI = "neo4j+s://68a13211.databases.neo4j.io"  # 你的Neo4j云数据库URI
NEO4J_USER = "neo4j"  # 用户名
NEO4J_PASSWORD = "QEJqrLMfOwRO1CKI0y8qkGC7IkHX15auiRvDGZYI6pE"  # 密码

# 初始化驱动程序
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 创建实体和关系的函数
def create_knowledge_graph(tx, entity, cui, connections):
    # 合并实体节点，并设置CUI属性，确保实体名为小写
    tx.run(
        "MERGE (e:Entity {name: $entity_name}) "
        "SET e.cui = $cui",
        entity_name=entity.lower(),  # 将实体名称转换为小写
        cui=cui
    )
    
    # 为每个连接的实体创建节点和关系，确保连接的实体名称为小写
    for connection in connections:
        tx.run(
            """
            MATCH (e:Entity {name: $entity_name})
            MERGE (connected:Entity {name: $connected_entity})
            SET connected.cui = $connected_cui
            MERGE (e)-[:RELATIONSHIP {type: $relationship}]->(connected)
            """,
            entity_name=entity.lower(),  # 将实体名称转换为小写
            connected_entity=connection['entity'].lower(),  # 将连接的实体名称转换为小写
            connected_cui=connection.get('cui', 'unknown'),  # 如果连接的实体没有CUI，则使用'unknown'
            relationship=connection['relationship']
        )

# 读取JSON文件并导入数据
def upload_knowledge_graph_to_neo4j(json_file):
    # 读取JSON文件
    with open(json_file, 'r') as file:
        data = json.load(file)
    
    # 使用Neo4j会话
    with driver.session() as session:
        # 遍历JSON数据中的每个实体
        for item in data:
            entity = item['entity']
            cui = item.get('cui', 'unknown')  # 如果实体没有CUI，设置为'unknown'
            connections = item['connections']
            # 使用Neo4j事务上传数据
            session.write_transaction(create_knowledge_graph, entity, cui, connections)

# 指定JSON文件的路径
json_file = './dr_knowledge_graph.json'

# 导入JSON数据到Neo4j
upload_knowledge_graph_to_neo4j(json_file)

# 关闭驱动程序
driver.close()
