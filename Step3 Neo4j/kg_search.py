from neo4j import GraphDatabase

# 连接Neo4j数据库的参数
NEO4J_URI = "neo4j+s://68a13211.databases.neo4j.io"  # 替换为您的Neo4j云数据库URI
NEO4J_USER = "neo4j"  # 用户名
NEO4J_PASSWORD = "QEJqrLMfOwRO1CKI0y8qkGC7IkHX15auiRvDGZYI6pE"  # 密码

# 初始化驱动程序
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 检查是否已经存在 Full-Text 索引的函数
def index_exists(tx, index_name):
    query = """
    SHOW INDEXES YIELD name
    WHERE name = $index_name
    RETURN name
    """
    result = tx.run(query, index_name=index_name)
    return result.single() is not None  # 如果存在返回True，否则False

# 创建 Full-Text 索引的函数（如果不存在）
def create_fulltext_index(tx):
    query = """
    CREATE FULLTEXT INDEX entityNameIndex FOR (n:Entity) ON EACH [n.name];
    """
    tx.run(query)

# 创建 Full-Text 索引（如果尚未存在）
def create_index():
    with driver.session() as session:
        index_name = "entityNameIndex"
        if not session.execute_read(index_exists, index_name):
            session.execute_write(create_fulltext_index)
            print(f"Full-Text 索引 '{index_name}' 已创建")
        else:
            print(f"Full-Text 索引 '{index_name}' 已存在，无需创建")

# 查询相似实体
def query_similar_entities(query_string):
    def find_similar_entities(tx, query_string):
        query = """
        CALL db.index.fulltext.queryNodes('entityNameIndex', $query_string) 
        YIELD node, score 
        RETURN node.name AS entity_name, score 
        ORDER BY score DESC
        """
        result = tx.run(query, query_string=query_string)
        return [record for record in result]  # 返回所有结果作为列表

    with driver.session() as session:
        result = session.execute_read(find_similar_entities, query_string)
        
        if result:
            # 对结果按得分排序并提取前5个实体
            top_entities = sorted(result, key=lambda x: x["score"], reverse=True)[:5]
            entity_names = [record["entity_name"] for record in top_entities]
            print(f"Top 5 matches for query '{query_string}': {entity_names}")
            
            return entity_names
        else:
            print(f"No matching entities found for query: {query_string}")
            return None

# 查询实体及其相关关系
def query_entity_and_relationships(entity_name):
    def find_entity_and_relationships(tx, entity_name):
        query = (
            # 查询出向关系
            "MATCH (e:Entity {name: $entity_name})-[r1]->(n1) "
            "WHERE e <> n1 "  # 防止自环
            # 查询入向关系
            "OPTIONAL MATCH (n2)-[r2]->(e:Entity {name: $entity_name}) "
            "WHERE r2.type IN ['clinical_signs'] "  # 使用 type(r2) 来获取关系类型
            # 返回两个方向的关系
            "RETURN e.name AS entity, "
            "r1.type AS rel1, n1.name AS node1, "
            "r2.type AS rel2, n2.name AS node2"
        )
        result = tx.run(query, entity_name=entity_name)
        return [record for record in result]  # 返回所有结果作为列表

    with driver.session() as session:
        result = session.execute_read(find_entity_and_relationships, entity_name)
        print(f"Relationships for entity: {entity_name}")
        for record in result:
            # 打印出向关系
            if record['node1']:
                print(f"{record['entity']} -[{record['rel1']}]→ {record['node1']}")
            # 打印入向关系
            if record['node2']:
                print(f"{record['node2']} -[{record['rel2']}]→ {record['entity']}")



# 运行流程
if __name__ == "__main__":
    # 创建 Full-Text 索引（如果尚未存在）
    create_index()

    # 查询与 "Intraretinal" 相似的实体
    query_string = "Fluorescein fundus angiography of the right eye started early with the formation of a patchy non-perfused area below the temporal macula, with a slight dilatation of small retinal vessels around the macula and gradual leakage of fluorescein, and a large number of laser spots with gradual"  # 替换为您要查询的实体名称
    best_entities = query_similar_entities(query_string)

    # 如果找到最佳匹配实体，查询其相关关系
    for best_entity in best_entities:
        query_entity_and_relationships(best_entity)

    # 关闭驱动程序
    driver.close()
